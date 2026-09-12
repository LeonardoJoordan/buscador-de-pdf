# LYNX Atlas

**Fast PDF Search & Indexing**

O LYNX Atlas é um aplicativo desktop para indexar coleções locais de PDFs e
encontrar rapidamente palavras e frases dentro de todos os documentos. A busca,
o índice e a renderização das páginas são executados localmente.

## Recursos

- Indexação recursiva de PDFs em uma pasta e suas subpastas.
- Sincronização de arquivos adicionados, alterados ou removidos.
- Busca exata, fora de ordem e aproximada.
- Resultados classificados visualmente por tipo de correspondência.
- Preview da página encontrada, zoom, navegação e realce dos termos.
- Busca direcionada em documentos selecionados.
- Aviso sobre formatos não indexados encontrados na pasta.
- Interface Qt/QML para Windows e Linux.

## Limitações

- Somente arquivos PDF são indexados.
- PDFs compostos apenas por imagens precisam passar por OCR antes da indexação.
- Arquivos DOCX, ODT e outros devem ser exportados para PDF pelo aplicativo de
  origem e colocados na pasta indexada.

## Privacidade

O aplicativo não envia documentos, consultas ou índices para serviços externos.
O banco SQLite é criado localmente no perfil do usuário. Não publique arquivos
`index.db`: eles podem conter todo o texto extraído e os caminhos dos documentos.

## Executar pelo código-fonte

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
```

No Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

No Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Testes

```bash
python -m unittest discover -s tests -v
```

## Gerar o pacote Windows

Instale as dependências de compilação:

```powershell
python -m pip install -U Nuitka ordered-set
python script_nuitka.py
```

O script cria a distribuição standalone e um ZIP em `build/nuitka-windows`.
Para gerar o instalador, abra `instalador.iss` no Inno Setup e compile-o.

## Gerar o Flatpak

As instruções estão em [FLATPAK.md](FLATPAK.md). O manifesto utilizado é
`com.leobelisario.LYNXAtlas.yaml`.

## Licença

O LYNX Atlas é distribuído sob a **GNU Affero General Public License v3.0 only
(AGPL-3.0-only)**. Consulte [LICENSE](LICENSE).

Essa escolha é necessária para a distribuição com a edição comunitária do
PyMuPDF/MuPDF. Uma distribuição proprietária requer uma licença comercial
apropriada da Artifex e uma nova análise das demais dependências.

Os componentes de terceiros mantêm suas próprias licenças. Consulte
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) e o diretório [licenses](licenses/).

## Contribuições

Ao enviar uma contribuição, você concorda em disponibilizá-la sob a mesma
licença AGPL-3.0-only do projeto.

## Código-fonte correspondente

O código-fonte correspondente a cada binário oficial deve ser publicado na tag
da mesma versão em:

<https://github.com/LeonardoJoordan/LYNX-Atlas>
