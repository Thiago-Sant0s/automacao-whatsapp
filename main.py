import gspread
from oauth2client.service_account import ServiceAccountCredentials

# conexão
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(creds)

# abre a planilha
planilha = client.open("ClientesTB").sheet1

# escreve uma linha
planilha.append_row(["Teste", "123456"])

print("✅ Funcionou!")
