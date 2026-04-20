# Como executar a automação

Passo a passo para rodar o robô do RPA Challenge na sua máquina.

---

## 1. O que você precisa ter

- **Python 3.10 ou superior** instalado (`python3 --version` no terminal).
- **Google Chrome** instalado (o script usa o Chrome).
- O arquivo **`challenge.xlsx`** na **mesma pasta** que `rpa_challenge.py`  
  - Baixe pelo site [rpachallenge.com](https://rpachallenge.com) → botão **Download Excel** na lateral de instruções.

---

## 2. Abrir o terminal na pasta do projeto

No Linux/macOS:

```bash
cd "/caminho/para/DynamicFormRPA"
```

No Windows (PowerShell ou CMD), use o caminho da sua pasta, por exemplo:

```cmd
cd C:\Users\SeuUsuario\...\DynamicFormRPA
```

---

## 3. (Opcional) Ambiente virtual

Recomendado para não misturar pacotes com outros projetos:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

---

## 4. Instalar dependências

```bash
pip install -r requirements.txt
```

Se `pip` não for encontrado, tente:

```bash
python3 -m pip install -r requirements.txt
```

---

## 5. Executar o robô

```bash
python3 rpa_challenge.py
```

Ou, no Windows:

```bash
python rpa_challenge.py
```

- Uma janela do **Chrome** deve abrir, acessar o site, clicar em **Start** e preencher o formulário **uma vez por linha** do Excel.
- No terminal aparecem linhas com data/hora (`log_etapa`).
- Ao terminar, o navegador fecha sozinho.

---

## 6. Onde ver o resultado

| O quê | Onde |
|--------|------|
| Screenshot final (score / tela final) | **`resultado.png`** na pasta do projeto |
| OK ou NOK por linha do Excel | **`resultado.log`** |
| Detalhes técnicos de erros | **`automation_debug.log`** |

---

## 7. Opções úteis (variáveis de ambiente)

**Outro arquivo Excel** (caminho completo ou relativo):

```bash
RPA_EXCEL="/home/usuario/Downloads/challenge.xlsx" python3 rpa_challenge.py
```

**Rodar sem abrir janela do navegador** (headless):

```bash
RPA_HEADLESS=1 python3 rpa_challenge.py
```

No Windows (PowerShell):

```powershell
$env:RPA_HEADLESS="1"; python rpa_challenge.py
```

**Outra URL** (se precisar de cópia espelho do desafio):

```bash
RPA_URL="https://rpachallenge.com" python3 rpa_challenge.py
```

---

## 8. Problemas comuns

| Problema | O que fazer |
|----------|-------------|
| `FileNotFoundError` para o Excel | Confirme que `challenge.xlsx` está na mesma pasta que `rpa_challenge.py` ou use `RPA_EXCEL=...`. |
| Erro ao importar `pandas` / `selenium` | Rode de novo: `pip install -r requirements.txt` no mesmo ambiente onde executa o script. |
| Chrome não abre ou erro de driver | Atualize o Chrome; Selenium 4 costuma baixar o driver compatível automaticamente. |
| `ModuleNotFoundError: openpyxl` | `pip install openpyxl` (já listado no `requirements.txt`). |

---

## 9. Documentação da solução

Para entender **como** o código mapeia campos dinâmicos, logs e rodadas, leia o **`README.md`** na raiz do projeto.
