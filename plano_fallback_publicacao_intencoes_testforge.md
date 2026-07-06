# Plano de Implementação — Publicação de Intenções do TestForge sem dependência obrigatória do Git

## 1. Objetivo da alteração

Implementar no TestForge um mecanismo de publicação da intenção gravada que funcione mesmo quando o usuário não possuir Git instalado, ou quando o `git.exe` estiver bloqueado por política corporativa.

A aplicação deverá tentar publicar a intenção nesta ordem:

```text
1. Git local, se disponível e funcional
2. Azure DevOps REST API, se Git não estiver disponível
3. Fila local em disco, se REST também falhar
```

O objetivo é preservar o comportamento desejado — a intenção virar arquivo versionado no repositório — mas sem depender obrigatoriamente do executável `git.exe`.

---

## 2. Escopo da alteração

A LLM deve alterar apenas a camada responsável por publicar a intenção após a gravação.

### Não deve alterar

```text
- fluxo de gravação da intenção;
- estrutura principal da intenção;
- UI do recorder, exceto se já existir mensagem de sucesso/erro;
- lógica de geração do script Playwright;
- EvidenceCollector;
- pipeline de instalação Python.
```

### Deve alterar ou criar

```text
- leitura da configuração gerada pelo instalador;
- camada abstrata de publicação;
- publisher via Git, se já existir;
- novo publisher via Azure DevOps REST API;
- publisher de fila local;
- logs claros de fallback;
- testes unitários dos fluxos principais.
```

---

## 3. Arquivo de configuração esperado

O instalador atualizado grava um arquivo na raiz do projeto instalado:

```text
.testforge-install-mode.env
```

Esse arquivo deve ser lido pela aplicação no momento da inicialização ou no momento da publicação da intenção.

Exemplo esperado:

```env
TESTFORGE_INSTALLER_DIR=C:\Users\c160698\Downloads\instalador
TESTFORGE_REPO_ROOT=C:\Users\c160698\AP\AUTOMATA-PRIMUS
TESTFORGE_TARGET_BRANCH=update-gravador
TESTFORGE_GIT_AVAILABLE=0
TESTFORGE_GIT_EXE=
TESTFORGE_INTENTION_PUBLISH_MODE=file_queue
TESTFORGE_INTENTION_OUTBOX=C:\Users\c160698\AP\TestForge\intention-outbox
TESTFORGE_REPO_ZIP=C:\Users\c160698\Downloads\instalador\AUTOMATA-PRIMUS.zip
```

A LLM deve implementar um carregador simples de `.env`, sem dependência obrigatória de pacote externo. Se já houver `python-dotenv` no projeto, pode usar. Caso contrário, criar parser próprio.

### Regras do parser

```text
- Ignorar linhas vazias.
- Ignorar linhas começadas por #.
- Separar chave e valor no primeiro =.
- Não fazer eval.
- Não imprimir valores sensíveis em log.
```

---

## 4. Nova variável de modo de publicação

A configuração atual criada pelo instalador usa:

```text
TESTFORGE_INTENTION_PUBLISH_MODE=git
```

ou:

```text
TESTFORGE_INTENTION_PUBLISH_MODE=file_queue
```

A alteração deve suportar também:

```text
TESTFORGE_INTENTION_PUBLISH_MODE=auto
```

### Comportamento recomendado

```text
auto:
  tenta Git
  se falhar, tenta Azure DevOps REST
  se falhar, salva em fila local

git:
  tenta Git
  se falhar, tenta REST
  se falhar, salva em fila local

azure_devops_rest:
  tenta REST
  se falhar, salva em fila local

file_queue:
  salva diretamente na fila local
```

Motivo: mesmo que o instalador marque `file_queue`, pode ser útil permitir que a aplicação tente REST antes de desistir, desde que existam as configurações necessárias.

---

## 5. Configurações necessárias para REST

A LLM deve adicionar suporte às seguintes variáveis de ambiente ou arquivo local de configuração:

```env
TESTFORGE_AZDO_BASE_URL=https://alm.ceaus.df.caixa/CEGTI
TESTFORGE_AZDO_PROJECT=AUTOMATA-PRIMUS
TESTFORGE_AZDO_REPOSITORY=AUTOMATA-PRIMUS
TESTFORGE_AZDO_BRANCH=update-gravador
TESTFORGE_AZDO_PAT=...
TESTFORGE_AZDO_SSL_VERIFY=false
```

Observações:

```text
- TESTFORGE_AZDO_PAT não deve ser versionado.
- Não gravar PAT em log.
- Se usar arquivo local para segredo, usar algo como:
  %USERPROFILE%\AP\TestForge\secrets.env
- Esse arquivo deve ficar fora do repositório.
```

---

## 6. Arquitetura proposta

Criar uma interface simples:

```python
class IntentionPublisher:
    def publish(self, intention: dict, metadata: dict | None = None) -> PublishResult:
        ...
```

Criar resultado padronizado:

```python
from dataclasses import dataclass

@dataclass
class PublishResult:
    ok: bool
    mode: str
    destination: str | None = None
    message: str | None = None
    error: str | None = None
```

Criar implementações:

```text
GitIntentionPublisher
AzureDevOpsRestIntentionPublisher
FileQueueIntentionPublisher
AutoIntentionPublisher
```

### Responsabilidades

```text
GitIntentionPublisher:
  mantém o comportamento atual via git.exe, se já existir.

AzureDevOpsRestIntentionPublisher:
  faz GET do objectId atual da branch.
  faz POST de push com novo arquivo JSON.

FileQueueIntentionPublisher:
  salva a intenção em arquivo local.
  nunca perde a gravação.

AutoIntentionPublisher:
  orquestra a ordem de fallback.
```

---

## 7. Fluxo detalhado de publicação

### 7.1 Fluxo principal

```text
1. Recorder finaliza a gravação da intenção.
2. Monta objeto intention em memória.
3. Chama publisher.publish(intention, metadata).
4. Publisher verifica modo configurado.
5. Se Git disponível:
   5.1 tenta publicar via Git.
   5.2 se sucesso, retorna ok.
   5.3 se falha, registra log e tenta REST.
6. REST:
   6.1 valida configuração mínima.
   6.2 busca objectId da branch.
   6.3 monta payload do commit.
   6.4 executa POST /pushes.
   6.5 se sucesso, retorna ok.
   6.6 se falha, registra log e usa fila local.
7. Fila local:
   7.1 gera nome único para arquivo.
   7.2 salva intenção em JSON.
   7.3 retorna ok com mode=file_queue.
```

### 7.2 Resultado esperado para o usuário

Se publicou por Git:

```text
Intenção publicada no repositório via Git.
```

Se publicou por REST:

```text
Intenção publicada no repositório via Azure DevOps REST API.
```

Se caiu na fila local:

```text
Git/API indisponíveis. A intenção foi salva localmente para envio posterior.
```

---

## 8. Implementação da Azure DevOps REST API

### 8.1 Descobrir objectId atual da branch

A API de push exige o `oldObjectId` da branch. Portanto, antes do `POST`, fazer uma chamada de consulta à referência da branch.

Endpoint lógico:

```text
GET {base_url}/{project}/_apis/git/repositories/{repository}/refs?filter=heads/{branch}&api-version=7.1
```

A resposta deve conter a referência da branch e seu `objectId`.

Se não encontrar a branch:

```text
- não criar branch automaticamente nesta primeira versão;
- registrar erro claro;
- cair para fila local.
```

### 8.2 Criar push com arquivo da intenção

Endpoint lógico:

```text
POST {base_url}/{project}/_apis/git/repositories/{repository}/pushes?api-version=7.1
```

Payload conceitual:

```json
{
  "refUpdates": [
    {
      "name": "refs/heads/update-gravador",
      "oldObjectId": "OBJECT_ID_ATUAL_DA_BRANCH"
    }
  ],
  "commits": [
    {
      "comment": "testforge: adiciona intenção gravada",
      "changes": [
        {
          "changeType": "add",
          "item": {
            "path": "/recordings/intencoes/SISTEMA/nome-da-intencao.json"
          },
          "newContent": {
            "content": "{...json...}",
            "contentType": "rawtext"
          }
        }
      ]
    }
  ]
}
```

---

## 9. Estratégia de nome do arquivo no repositório

A LLM deve criar uma função para gerar caminho seguro:

```python
def build_repo_intention_path(intention: dict) -> str:
    ...
```

Sugestão:

```text
/recordings/intencoes/{sistema}/{timestamp}-{slug}.json
```

Exemplo:

```text
/recordings/intencoes/SIMOV/20260706-142100-login-invalido.json
```

Regras:

```text
- Remover acentos do slug.
- Trocar espaços por hífen.
- Remover caracteres inválidos para path.
- Usar timestamp para reduzir colisão.
- Se não houver sistema, usar "geral".
- Se não houver nome do caso, usar "intencao".
```

---

## 10. Tratamento de conflito

Possível problema: duas pessoas publicam ao mesmo tempo na mesma branch.

Sintoma:

```text
POST /pushes falha por oldObjectId desatualizado
```

Comportamento esperado:

```text
1. Refazer GET da branch.
2. Tentar POST novamente uma vez.
3. Se falhar de novo, salvar em fila local.
```

Não implementar loop infinito.

---

## 11. Segurança

A LLM deve seguir estas regras:

```text
- Nunca gravar PAT em log.
- Nunca incluir PAT em exceções mostradas ao usuário.
- Nunca salvar PAT dentro do repositório.
- Se usar arquivo secrets.env, ele deve ficar fora do repo, por exemplo:
  %USERPROFILE%\AP\TestForge\secrets.env
- Se o projeto tiver .gitignore, garantir que secrets.env e .testforge-install-mode.env não sejam versionados se contiverem dados sensíveis.
```

---

## 12. Implementação sugerida de arquivos

A LLM deve procurar a estrutura atual do projeto. Se existir pacote `src/testforge`, adicionar algo próximo de:

```text
src/testforge/
  publishing/
    __init__.py
    config.py
    result.py
    base.py
    git_publisher.py
    azure_devops_rest_publisher.py
    file_queue_publisher.py
    auto_publisher.py
```

Se a estrutura atual for diferente, adaptar mantendo o conceito.

---

## 13. Código-base sugerido

### 13.1 `result.py`

```python
from dataclasses import dataclass


@dataclass
class PublishResult:
    ok: bool
    mode: str
    destination: str | None = None
    message: str | None = None
    error: str | None = None
```

### 13.2 `base.py`

```python
from abc import ABC, abstractmethod
from .result import PublishResult


class IntentionPublisher(ABC):
    @abstractmethod
    def publish(self, intention: dict, metadata: dict | None = None) -> PublishResult:
        raise NotImplementedError
```

### 13.3 `config.py`

```python
import os
from pathlib import Path


def load_env_file(path: str | Path) -> dict:
    path = Path(path)
    data = {}

    if not path.exists():
        return data

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()

    return data


def load_testforge_publish_config(repo_root: str | Path) -> dict:
    repo_root = Path(repo_root)

    config = {}
    config.update(load_env_file(repo_root / ".testforge-install-mode.env"))

    user_base = Path.home() / "AP" / "TestForge"
    config.update(load_env_file(user_base / "secrets.env"))

    for key, value in os.environ.items():
        if key.startswith("TESTFORGE_"):
            config[key] = value

    return config
```

### 13.4 `azure_devops_rest_publisher.py`

```python
import base64
import json
import re
import unicodedata
from datetime import datetime

import requests

from .base import IntentionPublisher
from .result import PublishResult


class AzureDevOpsRestIntentionPublisher(IntentionPublisher):
    def __init__(self, config: dict):
        self.config = config

    def publish(self, intention: dict, metadata: dict | None = None) -> PublishResult:
        try:
            self._validate_config()

            branch = self.config["TESTFORGE_AZDO_BRANCH"]
            old_object_id = self._get_branch_object_id(branch)
            repo_path = self._build_repo_path(intention)

            try:
                self._push_file(branch, old_object_id, repo_path, intention)
            except RuntimeError:
                old_object_id = self._get_branch_object_id(branch)
                self._push_file(branch, old_object_id, repo_path, intention)

            return PublishResult(
                ok=True,
                mode="azure_devops_rest",
                destination=repo_path,
                message="Intenção publicada via Azure DevOps REST API.",
            )

        except Exception as exc:
            return PublishResult(
                ok=False,
                mode="azure_devops_rest",
                error=str(exc),
            )

    def _validate_config(self):
        required = [
            "TESTFORGE_AZDO_BASE_URL",
            "TESTFORGE_AZDO_PROJECT",
            "TESTFORGE_AZDO_REPOSITORY",
            "TESTFORGE_AZDO_BRANCH",
            "TESTFORGE_AZDO_PAT",
        ]

        missing = [key for key in required if not self.config.get(key)]

        if missing:
            raise RuntimeError(
                "Configuração REST incompleta. Variáveis ausentes: "
                + ", ".join(missing)
            )

    def _headers(self):
        pat = self.config["TESTFORGE_AZDO_PAT"]
        token = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")

        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _ssl_verify(self):
        value = str(self.config.get("TESTFORGE_AZDO_SSL_VERIFY", "true")).lower()
        return value not in {"0", "false", "no", "nao", "não"}

    def _base_repo_url(self):
        base_url = self.config["TESTFORGE_AZDO_BASE_URL"].rstrip("/")
        project = self.config["TESTFORGE_AZDO_PROJECT"]
        repository = self.config["TESTFORGE_AZDO_REPOSITORY"]

        return f"{base_url}/{project}/_apis/git/repositories/{repository}"

    def _get_branch_object_id(self, branch: str) -> str:
        url = (
            f"{self._base_repo_url()}/refs"
            f"?filter=heads/{branch}&api-version=7.1"
        )

        response = requests.get(
            url,
            headers=self._headers(),
            verify=self._ssl_verify(),
            timeout=30,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Falha ao consultar branch {branch}: "
                f"{response.status_code} - {response.text}"
            )

        data = response.json()
        values = data.get("value", [])

        if not values:
            raise RuntimeError(f"Branch não encontrada: {branch}")

        return values[0]["objectId"]

    def _push_file(self, branch: str, old_object_id: str, repo_path: str, intention: dict):
        url = f"{self._base_repo_url()}/pushes?api-version=7.1"

        content = json.dumps(intention, ensure_ascii=False, indent=2)

        body = {
            "refUpdates": [
                {
                    "name": f"refs/heads/{branch}",
                    "oldObjectId": old_object_id,
                }
            ],
            "commits": [
                {
                    "comment": f"testforge: adiciona intenção {repo_path}",
                    "changes": [
                        {
                            "changeType": "add",
                            "item": {"path": repo_path},
                            "newContent": {
                                "content": content,
                                "contentType": "rawtext",
                            },
                        }
                    ],
                }
            ],
        }

        response = requests.post(
            url,
            headers=self._headers(),
            json=body,
            verify=self._ssl_verify(),
            timeout=30,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Falha ao publicar intenção via REST: "
                f"{response.status_code} - {response.text}"
            )

        return response.json()

    def _build_repo_path(self, intention: dict) -> str:
        sistema = (
            intention.get("sistema")
            or intention.get("system")
            or intention.get("app")
            or "geral"
        )

        nome = (
            intention.get("nome")
            or intention.get("name")
            or intention.get("title")
            or "intencao"
        )

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        sistema_slug = self._slugify(str(sistema))
        nome_slug = self._slugify(str(nome))

        return f"/recordings/intencoes/{sistema_slug}/{timestamp}-{nome_slug}.json"

    def _slugify(self, value: str) -> str:
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = value.strip("-")
        return value or "item"
```

### 13.5 `file_queue_publisher.py`

```python
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from .base import IntentionPublisher
from .result import PublishResult


class FileQueueIntentionPublisher(IntentionPublisher):
    def __init__(self, outbox_dir: str | Path):
        self.outbox_dir = Path(outbox_dir)

    def publish(self, intention: dict, metadata: dict | None = None) -> PublishResult:
        self.outbox_dir.mkdir(parents=True, exist_ok=True)

        name = (
            intention.get("nome")
            or intention.get("name")
            or intention.get("title")
            or "intencao"
        )

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}-{self._slugify(str(name))}.json"
        path = self.outbox_dir / filename

        payload = {
            "metadata": metadata or {},
            "intention": intention,
            "queued_at": datetime.now().isoformat(),
        }

        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return PublishResult(
            ok=True,
            mode="file_queue",
            destination=str(path),
            message="Intenção salva na fila local.",
        )

    def _slugify(self, value: str) -> str:
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = value.strip("-")
        return value or "intencao"
```

### 13.6 `auto_publisher.py`

```python
from pathlib import Path

from .azure_devops_rest_publisher import AzureDevOpsRestIntentionPublisher
from .file_queue_publisher import FileQueueIntentionPublisher
from .result import PublishResult


class AutoIntentionPublisher:
    def __init__(self, config: dict, git_publisher=None):
        self.config = config
        self.git_publisher = git_publisher

    def publish(self, intention: dict, metadata: dict | None = None) -> PublishResult:
        mode = self.config.get("TESTFORGE_INTENTION_PUBLISH_MODE", "auto")

        if mode in {"auto", "git"} and self.git_publisher is not None:
            result = self.git_publisher.publish(intention, metadata)
            if result.ok:
                return result

        if mode in {"auto", "git", "azure_devops_rest"}:
            rest_result = AzureDevOpsRestIntentionPublisher(self.config).publish(
                intention,
                metadata,
            )
            if rest_result.ok:
                return rest_result

        outbox = self.config.get(
            "TESTFORGE_INTENTION_OUTBOX",
            str(Path.home() / "AP" / "TestForge" / "intention-outbox"),
        )

        return FileQueueIntentionPublisher(outbox).publish(intention, metadata)
```

---

## 14. Integração no ponto atual de envio da intenção

A LLM deve localizar onde hoje o TestForge faz algo equivalente a:

```text
git add
git commit
git push
```

ou onde chama função de envio para o repositório.

Substituir por:

```python
from testforge.publishing.config import load_testforge_publish_config
from testforge.publishing.auto_publisher import AutoIntentionPublisher


def publish_recorded_intention(intention: dict, repo_root: str):
    config = load_testforge_publish_config(repo_root)

    publisher = AutoIntentionPublisher(
        config=config,
        git_publisher=None,  # ou publisher Git existente, se houver
    )

    return publisher.publish(
        intention=intention,
        metadata={
            "source": "testforge-recorder",
            "repo_root": repo_root,
        },
    )
```

Se já existir publisher Git, integrar:

```python
publisher = AutoIntentionPublisher(
    config=config,
    git_publisher=GitIntentionPublisher(config),
)
```

---

## 15. Ajuste mínimo no instalador

O instalador já grava:

```text
TESTFORGE_INTENTION_PUBLISH_MODE=git
```

ou:

```text
TESTFORGE_INTENTION_PUBLISH_MODE=file_queue
```

Recomendação para próxima revisão do instalador:

```text
TESTFORGE_INTENTION_PUBLISH_MODE=auto
```

Motivo:

```text
Mesmo sem Git, a aplicação ainda pode tentar REST antes de salvar em fila local.
```

Adicionar ao `.testforge-install-mode.env`, se possível:

```env
TESTFORGE_AZDO_BASE_URL=https://alm.ceaus.df.caixa/CEGTI
TESTFORGE_AZDO_PROJECT=AUTOMATA-PRIMUS
TESTFORGE_AZDO_REPOSITORY=AUTOMATA-PRIMUS
TESTFORGE_AZDO_BRANCH=update-gravador
TESTFORGE_AZDO_SSL_VERIFY=false
```

Não adicionar PAT no instalador.

---

## 16. Tratamento de autenticação

A LLM deve implementar busca do PAT nesta ordem:

```text
1. Variável de ambiente TESTFORGE_AZDO_PAT
2. Arquivo %USERPROFILE%\AP\TestForge\secrets.env
3. Se não existir, REST fica indisponível e cai para fila local
```

Não pedir PAT na UI nesta primeira alteração, salvo se já houver mecanismo de configuração segura.

Exemplo de `secrets.env`:

```env
TESTFORGE_AZDO_PAT=xxxxxxxxxxxxxxxxxxxx
```

Esse arquivo deve ficar fora do repositório.

---

## 17. Logs esperados

Adicionar logs claros, sem credenciais.

Exemplos:

```text
[INFO] Publicando intenção: modo auto
[INFO] Git indisponível. Tentando Azure DevOps REST API.
[INFO] Consultando objectId da branch update-gravador.
[INFO] Enviando intenção para /recordings/intencoes/SIMOV/...
[OK] Intenção publicada via Azure DevOps REST API.
```

Em caso de falha:

```text
[WARN] Falha na publicação REST. Salvando intenção na fila local.
[OK] Intenção salva em C:\Users\...\AP\TestForge\intention-outbox\...
```

Nunca logar:

```text
PAT
Authorization header
conteúdo sensível da intenção, se houver
```

---

## 18. Testes que a LLM deve criar

### 18.1 Testes unitários

Criar testes para:

```text
- load_env_file lê arquivo corretamente.
- load_env_file ignora comentários e linhas vazias.
- build_repo_path gera caminho válido.
- FileQueueIntentionPublisher cria arquivo JSON.
- AutoIntentionPublisher cai para file_queue se REST falhar.
- AzureDevOpsRestIntentionPublisher monta payload correto.
```

### 18.2 Testes com mock

Usar mock para `requests.get` e `requests.post`.

Cenários:

```text
1. Branch encontrada e POST bem-sucedido.
2. Branch não encontrada.
3. POST falha na primeira tentativa e funciona na segunda após novo GET.
4. POST falha duas vezes e AutoPublisher salva na fila local.
5. Configuração sem PAT cai para fila local.
```

---

## 19. Critérios de aceite

A alteração estará correta se:

```text
1. O TestForge continua publicando via Git quando Git estiver disponível.
2. Se Git não existir, o TestForge tenta REST.
3. Se REST estiver configurado corretamente, a intenção vira commit no repositório.
4. Se REST falhar, a intenção é salva localmente em intention-outbox.
5. Nenhuma credencial é exibida em log.
6. O sistema não perde a gravação da intenção.
7. A aplicação continua funcionando mesmo com Git bloqueado por GPO.
8. O instalador e a aplicação continuam compatíveis com ambiente CAIXA e fábrica.
```

---

## 20. Prompt pronto para entregar a outra LLM

```text
Você é uma LLM atuando como desenvolvedora Python no projeto TestForge.

Contexto:
O TestForge grava a intenção de testes web e hoje publica essa intenção no repositório usando Git. Porém, em algumas máquinas corporativas o git.exe não está instalado ou é bloqueado por política de grupo. O instalador foi ajustado para detectar Git e criar um arquivo .testforge-install-mode.env na raiz do projeto instalado. Também existe a possibilidade de instalar o projeto por ZIP.

Objetivo:
Implementar fallback de publicação de intenções sem depender do git.exe, usando Azure DevOps REST API. Se a publicação REST falhar, salvar a intenção em fila local.

Requisitos funcionais:
1. Criar uma camada de publicação com interface IntentionPublisher.
2. Implementar GitIntentionPublisher se já existir fluxo Git; se não existir, apenas preservar o ponto de extensão.
3. Implementar AzureDevOpsRestIntentionPublisher usando a API REST de pushes do Azure DevOps.
4. Implementar FileQueueIntentionPublisher para salvar a intenção em disco.
5. Implementar AutoIntentionPublisher que tenta:
   a. Git;
   b. Azure DevOps REST;
   c. fila local.
6. Ler configuração do arquivo .testforge-install-mode.env.
7. Ler segredos de variável de ambiente ou de %USERPROFILE%\AP\TestForge\secrets.env.
8. Nunca versionar ou logar PAT.
9. Não alterar o fluxo de gravação da intenção; alterar apenas o ponto de publicação.
10. Criar testes unitários e mocks para os fluxos principais.

Configurações esperadas:
TESTFORGE_INTENTION_PUBLISH_MODE=auto
TESTFORGE_INTENTION_OUTBOX=%USERPROFILE%\AP\TestForge\intention-outbox
TESTFORGE_AZDO_BASE_URL=https://alm.ceaus.df.caixa/CEGTI
TESTFORGE_AZDO_PROJECT=AUTOMATA-PRIMUS
TESTFORGE_AZDO_REPOSITORY=AUTOMATA-PRIMUS
TESTFORGE_AZDO_BRANCH=update-gravador
TESTFORGE_AZDO_PAT=<lido de variável de ambiente ou secrets.env>
TESTFORGE_AZDO_SSL_VERIFY=false

Implementação REST:
1. Fazer GET em:
   {base_url}/{project}/_apis/git/repositories/{repository}/refs?filter=heads/{branch}&api-version=7.1

2. Obter objectId da branch.

3. Fazer POST em:
   {base_url}/{project}/_apis/git/repositories/{repository}/pushes?api-version=7.1

4. Payload:
   - refUpdates com refs/heads/{branch} e oldObjectId.
   - commits com comentário e changes.
   - changeType add.
   - item.path apontando para /recordings/intencoes/{sistema}/{timestamp}-{slug}.json
   - newContent.content com JSON da intenção.
   - newContent.contentType rawtext.

Tratamento de erro:
- Se o GET falhar, cair para fila local.
- Se o POST falhar por conflito, refazer GET e tentar POST mais uma vez.
- Se falhar novamente, salvar em fila local.
- Nunca perder a intenção.

Arquivos sugeridos:
src/testforge/publishing/config.py
src/testforge/publishing/result.py
src/testforge/publishing/base.py
src/testforge/publishing/azure_devops_rest_publisher.py
src/testforge/publishing/file_queue_publisher.py
src/testforge/publishing/auto_publisher.py

Critérios de aceite:
- Com Git funcional, comportamento atual preservado.
- Sem Git, publicação REST funciona.
- Sem REST, intenção salva em outbox.
- Sem PAT, não quebra aplicação; cai para outbox.
- Logs não mostram credenciais.
- Testes unitários cobrem sucesso, falha e fallback.
```

---

## 21. Recomendação final

Orientar a outra LLM a implementar primeiro **REST + fila local**, sem mexer profundamente no fluxo Git atual. Isso reduz risco.

Ordem mais segura:

```text
1. Criar FileQueueIntentionPublisher.
2. Criar AzureDevOpsRestIntentionPublisher.
3. Criar AutoIntentionPublisher.
4. Plugar no ponto atual de publicação da intenção.
5. Só depois integrar com GitIntentionPublisher existente.
```

Assim, mesmo que a REST API tenha alguma restrição de rede ou autenticação no ambiente CAIXA, a gravação da intenção não será perdida: ela ficará na `intention-outbox` para envio posterior.
