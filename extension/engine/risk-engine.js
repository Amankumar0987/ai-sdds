class RiskEngine {

    calculate(result){

        let score = 0;

        switch(result.verdict){

            case "BLOCK":
                score = 100;
                break;

            case "WARN":
                score = 60;
                break;

            default:
                score = 0;
        }

        return {

            score,

            level:
                score >= 80 ? "HIGH" :
                score >= 40 ? "MEDIUM" :
                "LOW"

        };

    }

}

window.RiskEngine = RiskEngine;