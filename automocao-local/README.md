# Automação AWS - Análise de VPCs e Security Groups

Este projeto é uma ferramenta de automação para análise e geração de relatórios de VPCs (Virtual Private Cloud) e Security Groups na AWS.

## 🚀 Funcionalidades

- Validação automática de credenciais AWS
- Descoberta de regiões ativas com VPCs
- Análise de segurança de Security Groups
- Geração de relatórios em Excel
- Interface interativa via linha de comando

## 📋 Pré-requisitos

- Python 3.x
- Credenciais AWS configuradas
- Pip (gerenciador de pacotes Python)

## 🔧 Instalação

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITÓRIO]
cd automocao-local
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## ⚙️ Configuração

1. Configure suas credenciais AWS:
   - Via AWS CLI: `aws configure`
   - Ou crie um arquivo `.env` na pasta `config/` com suas credenciais

2. Verifique as configurações em `config/`

## 🚀 Uso

Execute o script principal:
```bash
python main.py
```

O programa irá:
1. Validar suas credenciais AWS
2. Apresentar um menu interativo
3. Coletar dados das VPCs e Security Groups
4. Gerar relatórios na pasta `output/`

## 📁 Estrutura do Projeto

```
automocao-local/
├── config/           # Arquivos de configuração
├── output/          # Relatórios gerados
├── src/             # Código fonte
├── venv/            # Ambiente virtual Python
├── main.py          # Script principal
├── requirements.txt # Dependências do projeto
└── README.md        # Este arquivo
```

## 🛠️ Tecnologias Utilizadas

- Python
- AWS SDK (boto3)
- Pandas
- Openpyxl
- Python-dotenv
- Psutil

## 📝 Notas

- O projeto requer permissões adequadas na AWS para acessar VPCs e Security Groups
- Os relatórios são gerados em formato Excel (.xlsx)
- O sistema monitora o uso de recursos (CPU, Memória) durante a execução

## 🤝 Contribuindo

1. Faça um Fork do projeto
2. Crie uma Branch para sua Feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).

## ✨ Agradecimentos

- AWS Documentation
- Comunidade Python
- Contribuidores do projeto
