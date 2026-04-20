"""
Automação RPA Challenge (https://rpachallenge.com)

Execução:
    1. Coloque o arquivo de teste `challenge.xlsx` na mesma pasta do script (ou defina RPA_EXCEL).
    2. Instale dependências: pip install -r requirements.txt
    3. Tenha o Google Chrome instalado (Selenium 4+ usa Selenium Manager para o driver).
    4. Rode: python rpa_challenge.py

Variáveis de ambiente opcionais:
    RPA_EXCEL   - caminho para o Excel (padrão: challenge.xlsx ao lado deste arquivo)
    RPA_URL     - URL do desafio (padrão: https://rpachallenge.com)
    RPA_HEADLESS - "1" para Chrome em modo headless

Mapeamento de campos:
    Os inputs são localizados pelo texto visível do <label> associado (requisito do desafio),
    nunca por índice ou posição fixa na página.

Rodadas (10x no desafio oficial):
    A cada Submit o site embaralha as posições e avança o contador (ROUND 2, ROUND 3, …).
    Para cada linha do Excel o fluxo é inteiro de novo: (1) mapear_campos() relendo todos os
    labels na tela atual; (2) preencher; (3) Submit; (4) aguardar o novo layout. Ou seja,
    não existe um mapa “fixo” entre rodadas — só o texto do label liga dado → input.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ---------------------------------------------------------------------------
# Configuração (caminho do Excel pode ser alterado por variável de ambiente)
# ---------------------------------------------------------------------------
CAMINHO_EXCEL = os.environ.get("RPA_EXCEL", str(Path(__file__).resolve().parent / "challenge.xlsx"))
URL_DESAFIO = os.environ.get("RPA_URL", "https://rpachallenge.com")
ARQUIVO_LOG_RESULTADOS = Path(__file__).resolve().parent / "resultado.log"
ARQUIVO_SCREENSHOT = Path(__file__).resolve().parent / "resultado.png"

WAIT_PADRAO = 20
MAX_TENTATIVAS_LINHA = 3
TENTATIVAS_MAPEAMENTO = 2
# O challenge.xlsx oficial tem 10 linhas = 10 rodadas (um submit por linha, com embaralhamento entre elas).
RODADAS_OFICIAIS_RPACHALLENGE = 10

T = TypeVar("T")


def log_etapa(mensagem: str) -> None:
    """Registra etapas no console com timestamp (formato solicitado)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{ts}] {mensagem}"
    print(linha, flush=True)


def log_resultado(numero_linha: int, status: str, observacao: str) -> None:
    """
    Grava resultado por linha em `resultado.log`.
    status: OK ou NOK
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bloco = (
        f"--- Linha {numero_linha} ---\n"
        f"Timestamp: {ts}\n"
        f"Status: {status}\n"
        f"Observação: {observacao}\n"
    )
    with open(ARQUIVO_LOG_RESULTADOS, "a", encoding="utf-8") as f:
        f.write(bloco + "\n")


def _configurar_logging_arquivo() -> None:
    """Log técnico complementar (Selenium/erros) em automation_debug.log."""
    log_path = Path(__file__).resolve().parent / "automation_debug.log"
    root = logging.getLogger()
    if root.handlers:
        return
    # Somente arquivo: o console fica reservado ao formato `log_etapa`.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
        force=True,
    )


def com_retry(
    operacao: Callable[[], T],
    max_tentativas: int,
    descricao: str,
    excecao_tipos: tuple = (
        StaleElementReferenceException,
        WebDriverException,
        TimeoutException,
        NoSuchElementException,
    ),
) -> T:
    """Reexecuta uma operação algumas vezes (útil para DOM dinâmico / instabilidade)."""
    ultima: Optional[BaseException] = None
    for tentativa in range(1, max_tentativas + 1):
        try:
            return operacao()
        except excecao_tipos as exc:  # type: ignore[misc]
            ultima = exc
            log_etapa(f"{descricao} — tentativa {tentativa}/{max_tentativas} falhou: {exc}")
    assert ultima is not None
    raise ultima


def ler_excel(caminho: str = CAMINHO_EXCEL) -> pd.DataFrame:
    """
    Lê o Excel com pandas. Cada linha é um envio.
    Os nomes das colunas devem coincidir com o texto dos labels na tela
    (ex.: 'First Name', 'Phone Number').
    """
    caminho_path = Path(caminho)
    if not caminho_path.is_file():
        raise FileNotFoundError(f"Arquivo Excel não encontrado: {caminho_path.resolve()}")

    df = pd.read_excel(caminho_path, engine="openpyxl")
    # Normaliza cabeçalhos (espaços extras não quebram o match com o label)
    df.columns = [str(c).strip() for c in df.columns]
    if df.empty:
        raise ValueError("O arquivo Excel não contém linhas de dados.")
    return df


def iniciar_driver() -> webdriver.Chrome:
    """Inicia o Chrome com WebDriverWait implícito via retorno do driver (uso explícito de Wait nas funções)."""
    opts = ChromeOptions()
    if os.environ.get("RPA_HEADLESS", "").strip() in ("1", "true", "yes", "on"):
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    service = ChromeService()
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(WAIT_PADRAO)
    return driver


def _input_associado_ao_label(driver: webdriver.Chrome, label: WebElement) -> WebElement:
    """
    Localiza o campo de texto relacionado ao label, sem usar ordem global na página:
    1) atributo 'for' -> id do input na página
    2) input irmão seguinte
    3) input dentro do mesmo container pai
    4) primeiro input de texto após o label no DOM
    """
    for_attr = label.get_attribute("for")
    if for_attr:
        return driver.find_element(By.ID, for_attr)

    try:
        return label.find_element(By.XPATH, "./following-sibling::input[not(@type='submit')]")
    except NoSuchElementException:
        pass
    try:
        return label.find_element(By.XPATH, "./../input[not(@type='submit')]")
    except NoSuchElementException:
        pass
    return label.find_element(
        By.XPATH,
        "./following::input[not(@type='submit') and (not(@type) or @type='text' or @type='email')][1]",
    )


def mapear_campos(driver: webdriver.Chrome, wait: WebDriverWait) -> Dict[str, WebElement]:
    """
    Percorre todos os <label> com texto na página *atual* e associa cada um ao <input> certo.

    Deve ser chamado de novo a cada rodada: depois de cada Submit o layout muda, então
    posições antigas não valem — só o texto do label.
    Retorno: { 'First Name': <input>, ... }
    """
    def _mapear() -> Dict[str, WebElement]:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "label")))
        labels = driver.find_elements(By.TAG_NAME, "label")
        mapa: Dict[str, WebElement] = {}
        for label in labels:
            texto = (label.text or "").strip()
            if not texto:
                continue
            try:
                inp = _input_associado_ao_label(driver, label)
            except NoSuchElementException:
                continue
            tipo = (inp.get_attribute("type") or "text").lower()
            if tipo == "submit":
                continue
            # Se houver labels duplicados, mantém o último encontrado (DOM atual)
            mapa[texto] = inp
        if not mapa:
            raise TimeoutException("Nenhum par label/input foi mapeado. Verifique se a página carregou o formulário.")
        return mapa

    return com_retry(_mapear, TENTATIVAS_MAPEAMENTO, "Mapear campos pelo texto do label")


def preencher_formulario(
    wait: WebDriverWait,
    mapa_label_input: Dict[str, WebElement],
    dados_linha: Dict[str, Any],
) -> None:
    """
    Preenche cada input cujo texto do label existe como coluna na linha do Excel.
    Usa WebDriverWait por campo (sem time.sleep).
    """
    for coluna, valor in dados_linha.items():
        if coluna not in mapa_label_input:
            continue
        el = mapa_label_input[coluna]
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            texto = ""
        else:
            texto = str(valor)

        wait.until(EC.element_to_be_clickable(el))
        el.clear()
        el.send_keys(texto)


def _linha_para_dict(series: pd.Series) -> Dict[str, Any]:
    d: Dict[str, Any] = {}
    for coluna, valor in series.items():
        if pd.isna(valor):
            d[str(coluna)] = ""
        else:
            d[str(coluna)] = valor
    return d


def _clicar_start(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    """Clica no botão Start que inicia o cronômetro do desafio."""
    # Pode ser button ou elemento com classe de botão material
    xpaths = [
        "//button[contains(normalize-space(.),'Start')]",
        "//a[contains(normalize-space(.),'Start')]",
        "//*[self::button or self::a][contains(translate(normalize-space(.), 'START', 'start'), 'start')]",
    ]
    ultimo: Optional[Exception] = None
    for xp in xpaths:
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
            btn.click()
            return
        except (TimeoutException, WebDriverException) as exc:
            ultimo = exc
            continue
    raise TimeoutException(f"Não foi possível clicar em Start: {ultimo}")


def _submeter_formulario(wait: WebDriverWait) -> None:
    submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='submit']")))
    submit.click()


def _aguardar_apos_submit(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    input_referencia: WebElement,
    ultima_linha: bool,
) -> None:
    """
    Após o submit o front re-renderiza os campos (posições mudam).
    Na última linha a UI pode exibir resultado/score sem o mesmo formulário — evita espera rígida.
    """
    curto = WebDriverWait(driver, min(12, WAIT_PADRAO))
    try:
        curto.until(EC.staleness_of(input_referencia))
    except TimeoutException:
        pass

    if ultima_linha:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        return

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "label")))
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='submit']")))


def _processar_uma_linha(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    numero_linha: int,
    dados: Dict[str, Any],
    ultima_linha: bool,
) -> None:
    """
    Uma rodada do desafio: mapear → preencher → submit → esperar novo layout.

    O primeiro mapear_campos() já roda sobre o formulário embaralhado da rodada atual
    (na 1ª vez após Start; nas seguintes, após o submit da rodada anterior).
    """
    def _tentativa() -> None:
        # Nova varredura de labels/inputs nesta rodada (posições podem ser totalmente diferentes).
        mapa = mapear_campos(driver, wait)
        preencher_formulario(wait, mapa, dados)

        # Referências frescas logo antes do submit (evita referências defasadas durante a digitação).
        mapa_submit = mapear_campos(driver, wait)
        if not mapa_submit:
            raise TimeoutException("Mapa vazio antes do submit.")
        qualquer_input = next(iter(mapa_submit.values()))
        _submeter_formulario(wait)
        _aguardar_apos_submit(driver, wait, qualquer_input, ultima_linha)

    com_retry(_tentativa, MAX_TENTATIVAS_LINHA, f"Processar linha {numero_linha}")


def main() -> int:
    _configurar_logging_arquivo()
    log_etapa("Iniciando automação")

    if ARQUIVO_LOG_RESULTADOS.exists():
        ARQUIVO_LOG_RESULTADOS.unlink()

    try:
        df = ler_excel(CAMINHO_EXCEL)
    except Exception as exc:
        log_etapa(f"Erro ao ler Excel: {exc}")
        return 1

    n_linhas = len(df)
    if n_linhas != RODADAS_OFICIAIS_RPACHALLENGE:
        log_etapa(
            f"Aviso: o Excel tem {n_linhas} linha(s). O desafio oficial tem "
            f"{RODADAS_OFICIAIS_RPACHALLENGE} rodadas (uma linha por submit); "
            "cada linha ainda dispara remapeamento completo pelo label."
        )

    driver: Optional[webdriver.Chrome] = None
    try:
        driver = iniciar_driver()
        wait = WebDriverWait(driver, WAIT_PADRAO)

        log_etapa(f"Abrindo {URL_DESAFIO}")
        driver.get(URL_DESAFIO)

        _clicar_start(driver, wait)
        log_etapa("Botão Start acionado — iniciando processamento das linhas")

        total = len(df)
        for numero, (_, row) in enumerate(df.iterrows(), start=1):
            log_etapa(
                f"Rodada {numero}/{total}: lendo labels e preenchendo de novo "
                f"(campos embaralhados na tela após cada submit; equivale à linha {numero} do Excel)"
            )
            dados = _linha_para_dict(row)
            try:
                _processar_uma_linha(driver, wait, numero, dados, ultima_linha=(numero == total))
                log_resultado(numero, "OK", "sucesso")
            except Exception as exc:
                logging.exception("Falha ao processar linha %s", numero)
                log_resultado(numero, "NOK", f"erro: {exc}")

        log_etapa("Fluxo concluído — capturando screenshot final")
        driver.save_screenshot(str(ARQUIVO_SCREENSHOT))
        log_etapa(f"Screenshot salvo em {ARQUIVO_SCREENSHOT.resolve()}")
        return 0
    finally:
        if driver is not None:
            driver.quit()
            log_etapa("Driver encerrado")


if __name__ == "__main__":
    raise SystemExit(main())
