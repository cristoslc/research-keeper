---
title: "Cloud - Ollama"
source-type: web
url: "https://docs.ollama.com/cloud"
fetched: 2026-04-03
---

# Ollama Cloud

## Cloud Models

Ollama's cloud models are a new kind of model that can run without a powerful GPU. Cloud models are automatically offloaded to Ollama's cloud service while offering the same capabilities as local models. This makes it possible to keep using local tools while running larger models that wouldn't fit on a personal computer.

### Running Cloud Models

Cloud models require an account on ollama.com. Sign in with:

```
ollama signin
```

Then run a cloud model:

```
ollama run gpt-oss:120b-cloud
```

Or via Python:

```python
from ollama import Client

client = Client()
for part in client.chat('gpt-oss:120b-cloud', messages=[{'role': 'user', 'content': 'Why is the sky blue?'}], stream=True):
    print(part['message']['content'], end='', flush=True)
```

Or JavaScript:

```javascript
import { Ollama } from "ollama";
const ollama = new Ollama();
const response = await ollama.chat({
  model: "gpt-oss:120b-cloud",
  messages: [{ role: "user", content: "Explain quantum computing" }],
  stream: true,
});
for await (const part of response) {
  process.stdout.write(part.message.content);
}
```

## Cloud API Access

Cloud models can also be accessed directly on ollama.com's API. In this mode, ollama.com acts as a remote Ollama host.

### Authentication

Create an API key at ollama.com/settings/keys, then:

```
export OLLAMA_API_KEY=your_api_key
```

### Generating a Response (Python)

```python
import os
from ollama import Client

client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + os.environ.get('OLLAMA_API_KEY')}
)

for part in client.chat('gpt-oss:120b', messages=[{'role': 'user', 'content': 'Why is the sky blue?'}], stream=True):
    print(part['message']['content'], end='', flush=True)
```

### Generating a Response (cURL)

```bash
curl https://ollama.com/api/chat \
  -H "Authorization: Bearer $OLLAMA_API_KEY" \
  -d '{
    "model": "gpt-oss:120b",
    "messages": [{"role": "user", "content": "Why is the sky blue?"}],
    "stream": false
  }'
```

## Local Only

Ollama can run in local-only mode by disabling cloud features.
