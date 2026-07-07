# Secrets Management

## अभी क्या है (Current state)

सभी secrets (`AI_SDDS_API_KEYS`, future DB passwords, आदि) environment
variables से आते हैं — `config.py`। यह छोटी टीम/single-server deployment
के लिए ठीक है, बशर्ते:
- `.env` फ़ाइल **कभी commit न हो** (`.gitignore` में है, `.secrets.baseline` से ऑडिटेड)
- `.env` फ़ाइल पर file permissions सीमित हों (`chmod 600 .env`)
- container/server logs में env vars print न हों

## एक टीम/प्रोडक्शन स्केल पर — असली Vault की ज़रूरत कब है

जब निम्न में से कोई भी सच हो, plain env vars छोड़कर एक secrets manager
(HashiCorp Vault, AWS Secrets Manager, या Doppler) पर जाएँ:
- एक से ज़्यादा सर्वर/container में same secret चाहिए
- secrets को बिना redeploy किए rotate करना है
- audit trail चाहिए ("किस key को कब किसने पढ़ा")
- अलग-अलग टीम members को अलग-अलग secrets तक पहुँच चाहिए

## सुझाया गया pattern (अभी कोड में wired नहीं — यह डिज़ाइन reference है)

`config.py` में secrets-पढ़ने का तरीका एक जगह abstract कर दें, ताकि
backend बदलना (.env → Vault) बाकी सारे कोड को बिना छेड़े हो सके:

```python
# config.py में concept-level उदाहरण
import os
import urllib.request
import json

def get_secret(name: str, default: str | None = None) -> str | None:
    vault_addr = os.getenv("AI_SDDS_VAULT_ADDR")
    vault_token = os.getenv("AI_SDDS_VAULT_TOKEN")

    if vault_addr and vault_token:
        # HashiCorp Vault KV-v2 read
        req = urllib.request.Request(
            f"{vault_addr}/v1/secret/data/ai-sdds/{name}",
            headers={"X-Vault-Token": vault_token},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.load(resp)
            return data["data"]["data"].get(name, default)

    # कोई Vault कॉन्फ़िगर नहीं — env var पर fall back (आज का तरीका)
    return os.getenv(name, default)
```

बाकी कोड (`api/auth.py`, `api/app.py`) सिर्फ़ `config.API_KEYS` पढ़ता है
— उसे यह जानने की ज़रूरत नहीं कि वो value `.env` से आई या Vault से।
यही separation of concerns असली फ़ायदा है: backend बदलने पर सिर्फ़
`config.py` बदलता है, बाकी कुछ नहीं।

## इस repo में अभी क्या लागू है (वास्तविक स्थिति, ईमानदारी से)

- ✅ `.env.example` टेम्पलेट, असली values कभी repo में नहीं
- ✅ `.gitignore` से `.env` बाहर
- ✅ `.pre-commit-config.yaml` + `detect-secrets` — गलती से commit होने से पहले रुकेगा
- 🔲 ऊपर वाला Vault pattern अभी **सिर्फ़ डिज़ाइन reference** है, `config.py` में wire नहीं किया गया — जब टीम स्केल हो तो यह सबसे पहला काम होना चाहिए
