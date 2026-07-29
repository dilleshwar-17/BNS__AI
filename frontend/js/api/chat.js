const chatAPI = {
    list() { return api.get('/chat/'); },
    create(title, mode) { return api.post('/chat/', { title, mode }); },
    getMessages(chatId) { return api.get(`/chat/${chatId}`); },
    send(chatId, message, mode) { return api.post(`/chat/${chatId}`, { message, mode }); },
    delete(chatId) { return api.del(`/chat/${chatId}`); },
};
