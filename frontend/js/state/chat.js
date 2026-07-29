const chatState = {
    currentId: null,
    chats: [],
    setCurrent(id) { this.currentId = id; },
    setChats(chats) { this.chats = chats; },
    getChat(id) { return this.chats.find(c => c.id === id); },
};
