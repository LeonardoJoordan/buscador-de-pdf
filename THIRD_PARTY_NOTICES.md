# Avisos de componentes de terceiros

Este arquivo acompanha as distribuições do LYNX Atlas. As licenças completas
indicadas abaixo estão em `LICENSE` e no diretório `licenses/`.

## PyMuPDF e MuPDF 1.28.2

Copyright Artifex Software, Inc. e contribuidores.

Licenciamento duplo: GNU Affero General Public License v3.0 ou licença comercial
da Artifex. Esta distribuição usa a opção AGPLv3. O LYNX Atlas e seu código-fonte
correspondente são, portanto, disponibilizados sob AGPL-3.0-only.

- Projeto: <https://pymupdf.readthedocs.io/>
- Licença comercial: <https://artifex.com/licensing/>
- Texto da AGPLv3: `LICENSE`

## PySide6, Shiboken6 e Qt 6.11.2

Copyright The Qt Company Ltd., Qt Project e contribuidores.

O projeto utiliza os módulos Qt Core, GUI, QML, Quick, Quick Controls e Dialogs
da edição comunitária, sob LGPLv3. As bibliotecas Qt são distribuídas como DLLs
compartilhadas e não foram modificadas. É permitido substituir essas DLLs por
versões compatíveis. Não se impõe restrição à engenharia reversa necessária para
depurar alterações nas bibliotecas LGPL.

- Qt for Python: <https://doc.qt.io/qtforpython-6/>
- Licenciamento Qt: <https://doc.qt.io/qt-6/licensing.html>
- LGPLv3: `licenses/LGPL-3.0.txt`
- GPLv3 incorporada pela LGPLv3: `licenses/GPL-3.0.txt`

Os pacotes Qt podem incorporar componentes adicionais de terceiros. Antes de
publicar cada binário, confira o conteúdo efetivo gerado e preserve todos os
avisos incluídos pelos pacotes oficiais.

## RapidFuzz 3.14.6

Copyright © 2020–presente Max Bachmann; copyright © 2011 Adam Cohen.

Distribuído sob a licença MIT. Texto completo em
`licenses/RapidFuzz-MIT.txt`.

## Python 3

Copyright Python Software Foundation e contribuidores.

O pacote standalone para Windows inclui o runtime Python. O texto da licença PSF
está em `licenses/Python-PSF.txt`.

## Nuitka e ordered-set

Ferramentas utilizadas somente durante a compilação. Nuitka é disponibilizado
sob Apache License 2.0 e incorpora componentes de runtime no executável gerado;
o texto está em `licenses/Apache-2.0.txt`. `ordered-set` é uma dependência de
compilação sob licença MIT e deve ser conferida novamente na versão usada para
cada release.
