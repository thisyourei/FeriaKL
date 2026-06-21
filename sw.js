/* Service Worker AUTODESTRUCTIVO.
   Durante el desarrollo no usamos SW. Si un navegador tenía uno registrado de antes,
   al actualizar descargará este archivo, que se elimina a sí mismo, borra las cachés
   y recarga las pestañas para que carguen la versión real (sin intermediario).
   El soporte offline se reactivará con un SW nuevo en la fase correspondiente. */
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map(k => caches.delete(k)));
    await self.registration.unregister();
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach(c => c.navigate(c.url));
  })());
});
