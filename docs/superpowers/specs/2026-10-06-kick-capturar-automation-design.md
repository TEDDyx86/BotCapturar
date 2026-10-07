# Automação local do comando `$capturar` no chat da Kick

**Data:** 2026-10-06
**Status:** Desenho aprovado pelo usuário

## Objetivo

Criar um programa local para Windows que envie a mensagem `$capturar` ao chat de uma live na Kick, sem exigir que a janela do navegador permaneça aberta. O usuário é moderador da live e tem autorização para enviar a mensagem.

## Comportamento principal

- O programa apresenta controles explícitos para **Iniciar** e **Parar**.
- Ao clicar em **Iniciar**, envia `$capturar` imediatamente.
- Depois do primeiro envio, repete a mensagem a cada 305 segundos (5 minutos e 5 segundos) enquanto estiver ligado.
- Ao clicar em **Parar**, cancela os envios futuros e encerra a atividade de chat.
- Não envia mensagens antes de o usuário clicar em **Iniciar**.

## Interface

Uma janela simples deve permitir informar o nome/slug do canal (por exemplo, `jukes` para `kick.com/jukes`), configurar as credenciais da Kick, iniciar e parar o envio, e acompanhar a situação do canal e o próximo envio. O usuário não precisa localizar nem digitar o ID numérico.

## Execução e integração

O aplicativo roda localmente em Windows e não depende de uma página da Kick aberta durante os envios. Para simplificar a configuração, o usuário informa somente o slug do canal. O programa obtém um App Access Token pelo fluxo `client_credentials`, consulta `GET /public/v1/channels?slug=<slug>` e guarda o `broadcaster_user_id` resolvido no Gerenciador de Credenciais do Windows. A consulta de canal usa dados públicos e não exige um escopo adicional do usuário. O envio usa a API REST oficial (`POST /public/v1/chat`) com OAuth de usuário e escopo `chat:write`; a conta autenticada precisa estar autorizada a enviar mensagens nesse canal. O navegador pode ser aberto durante o fluxo inicial de autorização OAuth, mas não precisa permanecer aberto depois disso.

## Falhas e recuperação

- Cada envio é um pedido HTTPS independente; a interface informa se a API está pronta, enviando, aguardando nova tentativa ou se requer autenticação.
- Só considera uma mensagem enviada quando a API retorna sucesso e `data.is_sent` é verdadeiro.
- Em falha transitória de rede ou resposta HTTP 429, informa o estado e tenta novamente com espera progressiva, respeitando `Retry-After` quando fornecido; não envia rajadas de compensação.
- Após uma mensagem aceita, agenda a próxima para 305 segundos depois.
- Erros de autorização/autenticação são mostrados ao usuário e não provocam repetição contínua; tokens vencidos devem ser atualizados pelo refresh OAuth documentado.
- Se o slug não localizar um canal, a interface mostra um erro e não habilita o envio.
- Parar cancela timers e impede pedidos futuros.

## Segurança e limites

- A autenticação deve usar uma conta autorizada para participar do chat.
- Credenciais não devem ser exibidas em logs nem armazenadas em texto simples sem necessidade.
- O envio é limitado à mensagem fixa `$capturar` e ao intervalo configurado de 305 segundos.

## Critérios de aceitação

1. O usuário consegue digitar apenas o slug do canal e iniciar/parar o programa pela janela.
2. O primeiro `$capturar` é enviado imediatamente após Iniciar.
3. Envios subsequentes ocorrem com intervalo de 305 segundos enquanto o programa está ativo.
4. Parar interrompe o ciclo e não deixa mensagens agendadas serem enviadas.
5. O estado de conexão e erros relevantes são visíveis na interface.
6. O programa opera sem manter uma janela de navegador aberta.
7. O programa resolve o slug pela API oficial sem pedir ao usuário o ID numérico; usa OAuth de usuário `chat:write` para enviar.

## Fora do escopo inicial

- Envio automático baseado na detecção de início/fim da live.
- Hospedagem em VPS ou execução quando o computador local estiver desligado.
- Configuração de múltiplas mensagens, canais ou intervalos.
