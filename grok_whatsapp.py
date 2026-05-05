from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import time
from datetime import datetime, timedelta
import re


PALAVRAS_FECHAMENTO = [
    "Pode sim", "Segue o pix.", 
    "pode fazer sim", "comprovante", "Sua placa está pronta", "Olá, sua placa esta pronta", "O rapaz está a caminho", "o rapaz está a caminho", "Assim que estiver a caminho avisamos", "Te aviso assim que estiver a caminho, pode ser?", "Assim que estiver pronta eu aviso", "Assim que estiver pronta", "Olá, sua placa esta pronta","Pode fazer", "Quando fica pronto?", "Fica pronta quando?", "Fica pronta hoje?","O rapaz está a caminho!!",
    "O rapaz está a caminho!",
    "Preciso do CPF, nome completo, CEP e numero da residência do proprietário, para o cadastro da placa no nosso sistema interno por favor",

]


scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(creds)
planilha = client.open("ClientesTB").sheet1


options = Options()
options.add_argument(r"user-data-dir=C:\whatsapp-bot")
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--start-maximized")


def calcular_tempo(texto):
    agora = datetime.now()
    try:
        hora = datetime.strptime(texto, "%H:%M")
        msg_time = agora.replace(hour=hora.hour, minute=hora.minute, second=0)
        if msg_time > agora:
            msg_time -= timedelta(days=1)
        return (agora - msg_time).total_seconds() / 3600
    except:
        texto_lower = texto.lower()
        if "ontem" in texto_lower:
            return 24
        if any(dia in texto_lower for dia in ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]):
            return 48
        return 999

def normalize_phone(tel):
    if not tel:
        return None
    digits = re.sub(r'\D', '', str(tel))
    if digits.startswith("55"):
        digits = digits[2:]
    return digits.lstrip("0")

def cliente_ja_fechou(driver):
    """Verifica se o cliente já fechou analisando as últimas 50 mensagens"""
    try:
        mensagens = driver.find_elements(
            By.XPATH, '//div[contains(@class, "message-in") or contains(@class, "message-out")]'
        )
        ultimas_mensagens = mensagens[-50:] if len(mensagens) > 50 else mensagens
        texto_conversa = " ".join([msg.text.lower() for msg in ultimas_mensagens])
        
        for palavra in PALAVRAS_FECHAMENTO:
            if palavra.lower() in texto_conversa:
                print(f"✅ Cliente já fechou - Detectado: '{palavra}'")
                return True
        return False
    except Exception as e:
        print(f"Erro ao verificar fechamento: {e}")
        return False


def extrair_telefone(driver):
    print("🔍 [EXTRAÇÃO TELEFONE] Iniciando...")
    telefone = None

    
    try:
        header_xpaths = [
            '//div[@id="main"]//header//span[contains(@class, "selectable-text")]',
            '//div[@id="main"]//header//div[contains(@class, "selectable-text")]',
            '//div[@id="main"]//header//span[@title]',
            '//div[@id="main"]//header//span',
            '//div[@id="main"]//header//div[contains(@class, "copyable-text")]'
        ]
        
        for xpath in header_xpaths:
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                text = el.text.strip()
                if re.search(r'\+?55', text) or len(re.sub(r'\D', '', text)) >= 10:
                    telefone = re.sub(r'\D', '', text)
                    if telefone.startswith("55"):
                        telefone = telefone[2:]
                    if len(telefone) >= 10:
                        print(f"✅ Telefone encontrado NO CABEÇALHO: {telefone}")
                        return telefone
    except:
        pass

    print(" → Não encontrou no cabeçalho. Tentando abrir perfil...")

    
    try:
        
        for _ in range(4):
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.7)

        
        click_xpaths = [
            '//div[@id="main"]//header//div[@role="button"]',
            '//div[@id="main"]//header//img',
            '//div[@id="main"]//header//div[contains(@class, "avatar")]',
            '//div[@id="main"]//header//span[@data-testid="conversation-header-title"]',
            '//div[@id="main"]//header//button',
            '//div[@id="main"]//header//div[contains(@class, "_amie")]'
        ]

        clicked = False
        for xpath in click_xpaths:
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.6)
                driver.execute_script("arguments[0].click();", element)
                time.sleep(4.2)   # Tempo aumentado para carregamento do painel
                print("✅ Painel do perfil aberto com sucesso")
                clicked = True
                break
            except:
                continue

        if not clicked:
            print("❌ Não foi possível abrir o painel do perfil")
            return None

        
        phone_xpaths = [
            '//span[contains(text(), "+55")]',
            '//div[contains(text(), "+55")]',
            '//div[@data-testid="contact-info-phone-number"]//span',
            '//span[contains(@class, "selectable-text") and contains(text(), "+55")]',
            '//div[contains(@class, "copyable-text") and contains(text(), "55")]',
            '//div[text()="Telefone" or text()="Número de telefone"]/following-sibling::div//span',
            '//span[contains(text(), "55") and string-length(translate(text(), " ()+-", "")) >= 10]'
        ]

        for xpath in phone_xpaths:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    text = el.text.strip()
                    if re.search(r'\+?55', text) or len(re.sub(r'\D', '', text)) >= 10:
                        telefone = re.sub(r'\D', '', text)
                        if telefone.startswith("55"):
                            telefone = telefone[2:]
                        if len(telefone) >= 10:
                            print(f"✅ Telefone encontrado NO PERFIL: {telefone}")
                            return telefone
            except:
                continue

    except Exception as e:
        print(f"❌ Erro ao extrair telefone: {str(e)[:120]}")
    finally:
        # Fecha o painel lateral
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1.3)
        except:
            pass

    print("⚠️ Não foi possível extrair o telefone desta conversa.")
    return None


try:
    driver = webdriver.Chrome(options=options)
    driver.get("https://web.whatsapp.com")
    print("Aguardando WhatsApp carregar...")
    WebDriverWait(driver, 90).until(EC.presence_of_element_located((By.XPATH, '//div[@id="pane-side"]')))
    print("WhatsApp carregado ✅\n")

    while True:
        try:
            print("🔄 Iniciando verificação...")
            dados = planilha.get_all_records()
            phones_in_sheet = {normalize_phone(linha.get("Telefone", "")): idx 
                              for idx, linha in enumerate(dados, start=2) 
                              if normalize_phone(linha.get("Telefone", ""))}

            print("Buscando lista de conversas...")
            processed = 0
            max_conversas = 300

            while processed < max_conversas:
                try:
                    
                    conversas = driver.find_elements(By.XPATH, '//div[@id="pane-side"]//div[contains(@class,"_ak8l")]')
                    
                    if processed >= len(conversas):
                        print("Não há mais conversas visíveis.")
                        break

                    
                    if processed > 0 and processed % 15 == 0:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", conversas[processed-1])
                            time.sleep(1.2)
                        except:
                            pass

                    conversa_atual = conversas[processed]

                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.8)

                    
                    try:
                        grupo_indicator = conversa_atual.find_element(By.XPATH, './/span[contains(@data-testid, "group") or contains(text(), "grupo")]')
                        if grupo_indicator:
                            print(f"→ Ignorando grupo ({processed+1})")
                            processed += 1
                            continue
                    except:
                        pass

                    
                    try:
                        saved_contact = conversa_atual.find_element(By.XPATH, './/span[contains(@title, "✓") or contains(@data-testid, "verified")]')
                        if saved_contact:
                            print(f"→ Ignorando contato salvo ({processed+1})")
                            processed += 1
                            continue
                    except:
                        pass

                    print(f"Processando conversa {processed+1} de ~{len(conversas)}...")
                    conversa_atual.click()
                    time.sleep(3.8)

                    
                    if cliente_ja_fechou(driver):
                        print(f"→ Ignorando cliente (já fechou o negócio)\n")
                        processed += 1
                        continue

                    telefone = extrair_telefone(driver)
                    if not telefone or len(telefone) < 10:
                        print("❌ Telefone inválido ou não encontrado. Pulando...\n")
                        processed += 1
                        continue

                    
                    tempo_texto = "00:00"
                    try:
                        spans = conversa_atual.find_elements(By.XPATH, './/span')
                        for span in spans:
                            text = span.text.strip()
                            if re.match(r'^\d{1,2}:\d{2}$', text) or any(p in text.lower() for p in ['ontem','hoje','seg','ter','qua','qui','sex','sab','dom']):
                                tempo_texto = text
                                break
                    except:
                        pass

                    
                    
                    horas = calcular_tempo(tempo_texto)
                    if horas < 3:
                        status = "VERDE"
                        acao = "Aguardar cliente"
                    elif horas <= 7:
                        status = "AMARELO"
                        acao = "Avaliar contato"
                    else:
                        status = "VERMELHO"
                        acao = "Entrar em contato AGORA"

                    
                    norm = normalize_phone(telefone)
                    if norm in phones_in_sheet:
                        idx = phones_in_sheet[norm]
                        planilha.update_cell(idx, 2, tempo_texto)
                        planilha.update_cell(idx, 3, status)
                        planilha.update_cell(idx, 4, acao)
                        print(f"✅ ATUALIZADO → {telefone} | {tempo_texto} | {status}")
                    else:
                        planilha.append_row([telefone, tempo_texto, status, acao])
                        print(f"✅ NOVO → {telefone} | {tempo_texto} | {status}")

                    print("-" * 60)
                    processed += 1

                except Exception as e:
                    print(f"Erro na conversa {processed+1}: {str(e)[:90]}")
                    processed += 1
                    time.sleep(1)

            print(f"✅ Ciclo concluído ({processed} conversas processadas). Aguardando 40 minutos...\n")
            time.sleep(40 * 60)

        except Exception as e:
            print(f"Erro no loop: {e}")
            time.sleep(15)

except Exception as e:
    print(f"Erro geral: {e}")
    input("Pressione ENTER para fechar...")