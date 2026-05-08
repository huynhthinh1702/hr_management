// Global live-update bus (Socket.IO)
(function () {
  if (!window.io) return;

  const listeners = new Set();
  let timer;

  function emitLocal(evt) {
    window.dispatchEvent(new CustomEvent("hr:global_changed", { detail: evt || {} }));
    listeners.forEach((cb) => {
      try {
        cb(evt || {});
      } catch (_) {}
    });
  }

  function debouncedEmit(evt) {
    clearTimeout(timer);
    timer = setTimeout(() => emitLocal(evt), 200);
  }

  const socket = io({ transports: ["websocket", "polling"] });
  socket.on("global_changed", (evt) => debouncedEmit(evt));

  window.HR_LIVE = {
    socket,
    onGlobalChange(cb) {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
  };
})();

