const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("agent007", {
  env: () => ipcRenderer.invoke("env"),
  hub: (method, route, body) => ipcRenderer.invoke("hub", method, route, body),
});