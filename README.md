# Sistema de Monitoramento das Usinas Solares
> Ainda estou adaptando o readme do projeto e fazendo algumas alterações para ele ficar open source, mas basicamente ele realiza o monitoramento do consumo de energia das Usinas Solares via API Solis, lendo os dados armazenados pela Solis, gerando os gráficos e enviando todos os dias o relatório do dia anterior de consumo, da semana anterior e do mes passado. Além disso, ele possui uma tarefa que envia alertas sobre o estado de cada usina e contém a tradução de cada tipo de alerta da Solis, porque o sistema nativamente usa apenas siglas. 

Vou incluir mais informações aqui.

### Organização da Arquitetura
```
src/
├── main               # função principal
     └──  ainda em desenvolvimento 
```

## Instalação

Instalar todas as dependencias do projeto 

```sh
pip install requeriments.txt
```


## Exemplo de uso

Ainda escrevendo essa parte, não sei se vou incluir ela mesmo.


## Configuração para Desenvolvimento

Ainda escrevendo essa parte.
```sh
npm test
```

## Comandos para Testar a Aplicação e seu funcionamento

Ainda escrevendo essa parte.

```sh
python smoke_test.py -full
```

## Outros recursos

Ainda escrevendo essa parte.

## Como contribuir

1. Faça o _fork_ do projeto (<https://github.com/rayssasza/solis/fork>)
2. Crie uma _branch_ para sua modificação (`git checkout -b feature/solis`)
3. Faça o _commit_ (`git commit -m 'Add commit'`)
4. _Push_ (`git push origin feature/solis`)
5. Crie um novo _Pull Request_

## Template do README.md

Esse README foi copiado a partir do template disponibilizado pelo projeto: <https://github.com/dbader/readme-template>
