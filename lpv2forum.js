import { io } from "socket.io-client";

const sio = io(BASE, {
    auth: {
        id: "client2"
    },
    transports: ["websocket"]
});

sio.on("challenge", (data) => {
    // signature
    sio.emit("verify", {});
});

sio.on("auth_ok", (data) => {
    sio.emit("request_history", {"room" : "general"});
    sio.emit("join_room", {"room" : "general", "user" : "User"});
});
