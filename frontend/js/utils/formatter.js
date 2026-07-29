const formatter = {
    date(dateStr) {
        return new Date(dateStr).toLocaleDateString();
    },
    time(dateStr) {
        return new Date(dateStr).toLocaleTimeString();
    },
    datetime(dateStr) {
        return `${this.date(dateStr)} ${this.time(dateStr)}`;
    },
};
