class ScanHistory {

    constructor() {
        this.key = "ai_sdds_history";
    }

    async getAll() {
        const data = await chrome.storage.local.get(this.key);
        return data[this.key] || [];
    }

    async add(scan) {

        const history = await this.getAll();

        history.unshift({
            file: scan.fileName,
            verdict: scan.verdict,
            findings: scan.findings,
            time: new Date().toISOString()
        });

        await chrome.storage.local.set({
            [this.key]: history.slice(0, 100)
        });
    }

    async clear() {
        await chrome.storage.local.remove(this.key);
    }

}

window.ScanHistory = ScanHistory;