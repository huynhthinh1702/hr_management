(function () {
  if (!window.io) return;
  if (window.HR_LIVE && window.HR_LIVE.socket) return;

  const globalListeners = new Set();
  const notificationListeners = new Set();
  let debounceTimer = null;

  function emitWindowEvent(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
  }

  function emitGlobal(evt) {
    emitWindowEvent("hr:global_changed", evt || {});
    globalListeners.forEach((cb) => {
      try {
        cb(evt || {});
      } catch (_) {}
    });
  }

  function emitNotification(evt) {
    emitWindowEvent("hr:notification", evt || {});
    notificationListeners.forEach((cb) => {
      try {
        cb(evt || {});
      } catch (_) {}
    });
  }

  function debouncedGlobal(evt) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => emitGlobal(evt), 120);
  }

  const socket = io({
    transports: ["websocket"],
    upgrade: false,
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 500,
    reconnectionDelayMax: 5000,
    randomizationFactor: 0.25,
    timeout: 10000,
  });

  socket.on("connect", () => emitWindowEvent("hr:socket_connected", { id: socket.id }));
  socket.on("disconnect", (reason) => emitWindowEvent("hr:socket_disconnected", { reason }));
  socket.on("connect_error", (error) => {
    emitWindowEvent("hr:socket_error", {
      message: error && error.message ? error.message : "connect_error",
    });
  });
  socket.on("global_changed", (evt) => debouncedGlobal(evt));
  socket.on("notification:new", (evt) => emitNotification({ type: "new", payload: evt || {} }));
  socket.on("notification:sync", (evt) => emitNotification({ type: "sync", payload: evt || {} }));

  window.HR_LIVE = {
    socket,
    onGlobalChange(cb) {
      globalListeners.add(cb);
      return () => globalListeners.delete(cb);
    },
    onNotification(cb) {
      notificationListeners.add(cb);
      return () => notificationListeners.delete(cb);
    },
  };
})();
