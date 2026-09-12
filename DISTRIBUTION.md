# Checklist de distribuição

Este documento é um checklist técnico, não aconselhamento jurídico.

## Antes de publicar o repositório

- Confirmar que todo o código próprio pode ser publicado sob AGPL-3.0-only.
- Confirmar a titularidade ou permissão de uso de `icone.png`, nome e identidade visual.
- Não versionar bancos SQLite, PDFs pessoais, builds, caches ou o repositório Flatpak local.
- Revisar `git status` e o histórico em busca de documentos ou segredos.
- Se bancos ou documentos já foram enviados ao remoto, reescrever o histórico
  antes de torná-lo público e considerar esses dados previamente expostos.
- Atualizar versão no `instalador.iss` e criar uma tag equivalente.

## Obrigações centrais da AGPLv3

- Fornecer a licença e os avisos de copyright aos destinatários.
- Disponibilizar o código-fonte correspondente completo da versão distribuída,
  incluindo scripts necessários para compilar e instalar.
- Licenciar o trabalho coberto como um todo sob AGPLv3, sem impor restrições
  adicionais incompatíveis.
- Informar ausência de garantia e preservar os avisos legais apropriados.
- Se futuramente houver uso por rede, oferecer aos usuários remotos uma forma
  clara de obter o código-fonte correspondente da versão executada.
- Não aplicar DRM ou termos que impeçam os direitos concedidos pela licença.

## Obrigações centrais da LGPLv3 do Qt/PySide6

- Incluir os textos GPLv3 e LGPLv3 e um aviso claro de uso das bibliotecas.
- Distribuir Qt como bibliotecas compartilhadas substituíveis, ou fornecer os
  materiais de relink exigidos pela LGPL.
- Permitir engenharia reversa para depuração de modificações nas bibliotecas LGPL.
- Disponibilizar o código-fonte das bibliotecas Qt modificadas; atualmente não há modificações.
- Preservar avisos de terceiros presentes na distribuição oficial do Qt.

## Antes de publicar um instalador ou ZIP

- Gerar o pacote exclusivamente a partir da tag pública da mesma versão.
- Confirmar que `LICENSE`, `README.md`, `THIRD_PARTY_NOTICES.md` e `licenses/`
  estão dentro do pacote final.
- Inventariar DLLs e componentes do diretório `.dist` e conferir suas licenças.
- Testar a substituição das DLLs Qt por uma compilação compatível.
- Publicar o código-fonte ou link correspondente ao lado do binário no GitHub Release.
- Guardar uma cópia exata do código-fonte correspondente pelo período exigido
  caso seja usado o modelo de oferta escrita da AGPL.
- Se a distribuição for comercial, verificar também os termos vigentes do Inno
  Setup; seus mantenedores solicitam a aquisição de licença para uso comercial.

## Alternativa proprietária

Para distribuir uma versão fechada, obtenha licença comercial do PyMuPDF/MuPDF
com a Artifex e licença comercial do Qt se não for possível cumprir a LGPLv3.
Faça uma nova auditoria antes da distribuição.
