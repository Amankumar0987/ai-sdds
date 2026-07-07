class Scanner {

    constructor(scanFunction){
        this.scanFunction = scanFunction;
    }

    async scan(file){

        console.log("Scanning:", file.name);

        return await this.scanFunction(file);

    }

}

window.Scanner = Scanner;