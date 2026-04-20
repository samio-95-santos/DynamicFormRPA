# DynamicFormRPA — RPA Challenge (rpachallenge.com)

Automação em **Python** com **Selenium** e **pandas** que lê um arquivo Excel, preenche o formulário dinâmico do [RPA Challenge](https://rpachallenge.com), registra logs e gera um screenshot final com o resultado (score) na tela.

**Só quer rodar o projeto?** Siga o passo a passo em **[COMO_EXECUTAR.md](COMO_EXECUTAR.md)**.

---

## O que o desafio exige

1. Dados vêm de uma planilha (uso do **`challenge.xlsx`** oficial ou equivalente).
2. Após clicar em **Start**, o cronômetro e as rodadas começam.
3. A cada **Submit**, o site **embaralha** a posição dos campos e avança o indicador de rodada (por exemplo **ROUND 2**, **ROUND 3**…).
4. O robô precisa **identificar cada campo pelo texto do label**, não pela posição na página.
5. No arquivo oficial há **10 linhas** → **10 envios** (10 rodadas com layout novo a cada vez).

Esta solução segue esse modelo: **a cada linha do Excel** o fluxo **remapeia** todos os labels da tela atual, preenche e submete de novo.

---

## Como a solução funciona

### Fluxo geral

| Etapa | Descrição |
|--------|------------|
| 1 | `ler_excel()` — lê o Excel com pandas; cabeçalhos normalizados (trim). |
| 2 | `iniciar_driver()` — abre o Chrome (Selenium 4 gerencia o ChromeDriver na maioria dos ambientes). |
| 3 | Abre o site, `log_etapa()` no console. |
| 4 | Clica em **Start** (`_clicar_start`). |
| 5 | Para **cada linha** do DataFrame: `mapear_campos()` → `preencher_formulario()` → Submit → espera o novo DOM (`_aguardar_apos_submit`). |
| 6 | `log_resultado()` grava OK/NOK por linha em `resultado.log`. |
| 7 | Ao terminar todas as linhas: **`resultado.png`** na pasta do projeto. |

### Campos dinâmicos (regra principal)

A função **`mapear_campos()`**:

- Localiza todos os elementos **`<label>`** com texto visível.
- Para cada label, encontra o **`<input>`** associado (atributo `for`, irmão seguinte, mesmo container ou primeiro input após o label no DOM), ignorando o botão Submit.
- Monta um dicionário **`{ "First Name": elemento_input, "Email": elemento_input, … }`**.

A função **`preencher_formulario()`** preenche só onde o **nome da coluna do Excel** é **igual** ao texto do label (por exemplo `First Name`, `Role in Company`, `Phone Number`).

Assim, **mesmo que os campos mudem de lugar** a cada Submit, na **próxima rodada** o código **varre de novo** a página e volta a ligar dado → campo pelo **rótulo**, não pelo índice visual.

### Esperas (sem `time.sleep`)

Todas as esperas usam **`WebDriverWait`** e condições do Selenium (`presence_of_element_located`, `element_to_be_clickable`, `staleness_of`, etc.).

### Retry

- **`com_retry()`** — reexecuta o processamento de uma linha em caso de falhas típicas de DOM (elemento obsoleto, timeout, etc.).
- O mapeamento também pode ser tentado mais de uma vez em situações instáveis.

### Tratamento de erros

Cada linha roda dentro de `try/except` em `main()`: em erro, grava **NOK** em `resultado.log` e **continua** para a próxima linha.

---

## Pré-requisitos

- **Python 3.10+** (recomendado).
- **Google Chrome** instalado.
- Arquivo **`challenge.xlsx`** na mesma pasta que `rpa_challenge.py` (ou caminho via `RPA_EXCEL`).

---

## Instalação e execução

```bash
cd DynamicFormRPA
pip install -r requirements.txt
python rpa_challenge.py
```

### Variáveis de ambiente (opcional)

| Variável | Função |
|----------|--------|
| `RPA_EXCEL` | Caminho absoluto ou relativo do Excel (padrão: `challenge.xlsx` ao lado do script). |
| `RPA_URL` | URL do desafio (padrão: `https://rpachallenge.com`). |
| `RPA_HEADLESS` | Defina como `1` para rodar o Chrome sem janela visível. |

Exemplo:

```bash
RPA_EXCEL=/caminho/para/meu.xlsx python rpa_challenge.py
```

---

## Arquivos gerados

| Arquivo | Conteúdo |
|---------|-----------|
| **`resultado.png`** | Screenshot da tela **após a última linha** (útil para evidenciar score/tela final). |
| **`resultado.log`** | Por linha: timestamp, **Status** (OK/NOK) e **Observação** (sucesso ou mensagem de erro). |
| **`automation_debug.log`** | Log técnico complementar (ex.: stack traces de exceções). |

O console exibe mensagens no formato **`[AAAA-MM-DD HH:MM:SS] mensagem`** via `log_etapa()`.

---

## Estrutura do código (`rpa_challenge.py`)

Funções principais alinhadas ao desafio:

- `ler_excel()` — leitura da planilha.
- `iniciar_driver()` — Chrome + opções.
- `mapear_campos()` — label → input na página atual.
- `preencher_formulario()` — preenchimento guiado pelo mapa e pelas colunas da linha.
- `log_etapa()` — etapas no console.
- `log_resultado()` — resultados em arquivo.
- `main()` — orquestração do fluxo completo.

Constante **`RODADAS_OFICIAIS_RPACHALLENGE = 10`**: se o Excel não tiver 10 linhas, um **aviso** é registrado no log de etapas; o número real de submits continua sendo **`len(df)`** (uma linha = uma rodada).

---

## Obter o `challenge.xlsx` oficial

No site, use o botão **Download Excel** na barra lateral das instruções, ou o link direto da planilha oferecido em [rpachallenge.com](https://rpachallenge.com).

---

## Dependências

Definidas em `requirements.txt`:

- `pandas`, `openpyxl` — leitura do `.xlsx`.
- `selenium` — automação do navegador.

---

## Licença / uso

Projeto de exemplo para o RPA Challenge; adapte conforme a política da sua organização ou avaliação técnica.
