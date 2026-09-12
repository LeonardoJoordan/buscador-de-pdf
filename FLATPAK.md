# Flatpak do LYNX Atlas

O manifesto `com.leobelisario.LYNXAtlas.yaml` segue o modelo fornecido e usa
GNOME Platform/SDK 47. As versões das dependências vêm de `requirements.txt`.
Este é um manifesto para compilação local, com acesso à rede durante o `pip
install`. Para publicar no Flathub, será necessário preparar fontes de
dependências para instalação offline e revisar runtime, ícone e metadados.

Na raiz do projeto, com `flatpak-builder` e o remoto Flathub disponíveis:

```sh
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47
flatpak-builder --repo=repo --force-clean build-dir com.leobelisario.LYNXAtlas.yaml
flatpak build-bundle repo LYNXAtlas.flatpak com.leobelisario.LYNXAtlas
flatpak install --user --reinstall LYNXAtlas.flatpak
flatpak run com.leobelisario.LYNXAtlas
```

O comando de compilação recria `build-dir`. O pacote instala os scripts
Python, os arquivos QML necessários e o `icone.png` de 512 × 512 pixels;
não inclui o ambiente virtual, testes, banco de dados atual ou backups.
O atalho usa o ícone próprio, instalado com o identificador do aplicativo.

O índice do Flatpak fica em
`~/.var/app/com.leobelisario.LYNXAtlas/data/index.db`. A primeira execução cria
um índice vazio; selecione novamente as pastas que deseja indexar. As
configurações também ficam isoladas na pasta do aplicativo.

A permissão `home:ro` permite ler os PDFs da pasta pessoal sem modificá-los.
Para indexar arquivos de outro local, libere a pasta necessária, por exemplo:

```sh
flatpak override --user --filesystem=/mnt/documentos:ro com.leobelisario.LYNXAtlas
```

A prévia interna usa PyMuPDF. A abertura externa depende do `xdg-open`/portal
disponível no runtime; os leitores instalados no sistema não são executáveis
diretamente de dentro do sandbox, e a seleção da página pode não ser preservada.

Referência: [documentação de compilação do Flatpak](https://docs.flatpak.org/en/latest/first-build.html).
