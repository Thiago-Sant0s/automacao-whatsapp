from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials 

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(creds)

planilha = client.open("ClientesTB").sheet1
dados = planilha.get_all_records()

print(dados)

agora = datetime.now() 

for i, linha in enumerate(dados, start=2):
    print("\n---NOVA LINHA---")
    print(linha)

    ultimo_contato = linha["Ultimo Contato"]
    print("Ultimo contato:", ultimo_contato)

    if ultimo_contato == "":
        print("Pulou porque está vazio")
        continue

    data_contato = datetime.strptime(ultimo_contato, "%Y-%m-%d %H:%M")
    horas = (agora - data_contato).total_seconds() / 3600
    print("Horas:", horas)

    # ✅ DEFINE STATUS
    if horas < 3:
        status = "VERDE"
        acao = "Aguardar cliente"
    elif horas < 7:
        status = "AMARELO"
        acao = "Avaliar contato"
    else:
        status = "VERMELHO"
        acao = "Entrar em contato agora"

    # ✅ ESCREVE SEMPRE (FORA DO IF)
    planilha.update_cell(i, 4, status)
    planilha.update_cell(i, 5, acao)

    print("Escreveu na planilha:", status, "-", acao)