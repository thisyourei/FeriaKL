"""Boleta digital: genera el PDF de una venta y la envía por correo.

El PDF tiene formato de comprobante angosto (estilo ticket de 80 mm). El envío
por correo usa SMTP (smtplib, biblioteca estándar) con el PDF como adjunto.
"""
from datetime import timezone, timedelta

from fpdf import FPDF

# Chile usa UTC-3 (sin horario de verano vigente para este uso simple).
_TZ_CL = timezone(timedelta(hours=-3))


def folio(sale: dict) -> str:
    """Folio corto y legible derivado del id de la venta."""
    return str(sale.get("id", ""))[-6:].upper() or "000000"


def _money(n) -> str:
    """Formatea pesos chilenos: 5500 -> $5.500."""
    try:
        n = int(round(float(n)))
    except (TypeError, ValueError):
        n = 0
    return "$" + f"{n:,}".replace(",", ".")


def _metodo(m: str) -> str:
    return {"efectivo": "Efectivo", "transferencia": "Transferencia"}.get(m, m or "—")


def build_pdf(sale: dict, business_name: str) -> bytes:
    """Construye el PDF de la boleta y devuelve sus bytes."""
    items = sale.get("items", [])
    # Altura dinámica según la cantidad de líneas.
    extra = 0
    if sale.get("metodo_pago") == "efectivo" and sale.get("pagado_con"):
        extra = 12
    alto = 70 + len(items) * 7 + extra
    pdf = FPDF(orientation="P", unit="mm", format=(80, alto))
    pdf.set_auto_page_break(False)
    pdf.set_margins(6, 6, 6)
    pdf.add_page()
    ancho = 80 - 12  # ancho útil

    # Encabezado
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(ancho, 7, business_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(ancho, 5, f"Boleta #{folio(sale)}", align="C", new_x="LMARGIN", new_y="NEXT")
    fecha = sale.get("created_at")
    if fecha is not None:
        try:
            fecha_txt = fecha.astimezone(_TZ_CL).strftime("%d-%m-%Y %H:%M")
        except Exception:
            fecha_txt = str(fecha)
        pdf.cell(ancho, 5, fecha_txt, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(6, pdf.get_y(), 74, pdf.get_y())
    pdf.ln(2)

    # Ítems
    pdf.set_font("Helvetica", "", 9)
    for it in items:
        nombre = str(it.get("nombre", ""))
        cant = it.get("cantidad", 0)
        cant_txt = (f"{cant:g}")
        # Línea 1: cantidad x nombre  (recortado para que quepa)
        etiqueta = f"{cant_txt} x {nombre}"
        if len(etiqueta) > 32:
            etiqueta = etiqueta[:31] + "…"
        pdf.cell(ancho * 0.66, 6, etiqueta, new_x="RIGHT", new_y="TOP")
        pdf.cell(ancho * 0.34, 6, _money(it.get("subtotal", 0)), align="R",
                 new_x="LMARGIN", new_y="NEXT")

    pdf.ln(1)
    pdf.line(6, pdf.get_y(), 74, pdf.get_y())
    pdf.ln(2)

    # Total
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(ancho * 0.5, 7, "TOTAL", new_x="RIGHT", new_y="TOP")
    pdf.cell(ancho * 0.5, 7, _money(sale.get("total", 0)), align="R",
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(ancho, 5, f"Pago: {_metodo(sale.get('metodo_pago'))}", new_x="LMARGIN", new_y="NEXT")
    if sale.get("metodo_pago") == "efectivo" and sale.get("pagado_con"):
        paga = float(sale["pagado_con"])
        vuelto = paga - float(sale.get("total", 0))
        pdf.cell(ancho, 5, f"Paga con: {_money(paga)}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(ancho, 5, f"Vuelto: {_money(max(vuelto, 0))}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(ancho, 5, "¡Gracias por su compra!", align="C", new_x="LMARGIN", new_y="NEXT")

    salida = pdf.output()
    return bytes(salida)


def send_receipt_email(to_email: str, sale: dict, pdf_bytes: bytes, settings) -> None:
    """Envía la boleta en PDF por correo vía SMTP. Lanza ValueError si no hay SMTP configurado."""
    import smtplib
    import ssl
    from email.message import EmailMessage

    if not settings.smtp_host:
        raise ValueError("El envío por correo no está configurado en el servidor.")

    remitente = settings.smtp_from or settings.smtp_user
    if not remitente:
        raise ValueError("Falta configurar el remitente del correo (smtp_from/smtp_user).")

    f = folio(sale)
    msg = EmailMessage()
    msg["Subject"] = f"Boleta {settings.business_name} #{f}"
    msg["From"] = remitente
    msg["To"] = to_email
    msg.set_content(
        f"¡Gracias por su compra en {settings.business_name}!\n\n"
        f"Adjuntamos su boleta #{f} en PDF.\n"
        f"Total: {_money(sale.get('total', 0))}\n"
    )
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                       filename=f"boleta-{f}.pdf")

    if settings.smtp_port == 465:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ctx, timeout=20) as s:
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
            s.ehlo()
            s.starttls(context=ssl.create_default_context())
            s.ehlo()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
