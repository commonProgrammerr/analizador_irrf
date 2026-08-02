# Design — Flags dinâmicos `--<name>` na CLI

**Data:** 2026-08-01
**Status:** Aprovado (2026-08-01)
**Escopo:** CLI apenas (web permanece com os 4 campos fixos)

## Contexto

Hoje a CLI aceita exatamente quatro flags fixos para os arquivos de resposta:
`--sniff`, `--molhada`, `--umida`, `--seca`. O usuário quer passar nomes
arbitrários: `--<name> <arquivo>`, onde `<name>` é escolhido por ele e vira a
coluna no relatório.

O pipeline já é flexível: `processar()` em `matcher.py` recebe
`arquivos_formulario: Dict[str, str]` e usa as chaves como colunas. Os
gargalos são a camada CLI (`cli.py`, `__init__.py`) e os rótulos do
`report.py`.

## Mecanismo (abordagem A — aprovada)

Usar `context_settings=dict(allow_extra_args=True, ignore_unknown_options=True)`
no comando click. Opções conhecidas (`--nomes`, `--amostras`, etc.) continuam
sendo consumidas normalmente; tudo que não casa vira pares em `ctx.args`
(validado empiricamente: `['--sniff', 'a.csv', '--faro-seco=b.csv']`).

Sem dependências novas; rich_click não interfere (só patcheia o help).

## Mudanças por arquivo

### `src/analizador_irrf/cli.py`

- **Remover** `_opts_form` (lista dos 4 `click.option` fixos) e o loop que os
  aplica em `shared_options`.
- **`coletar_arquivos_formulario(args: List[str]) -> Dict[str, str]`** — nova
  assinatura (antes: parâmetros fixos `sniff/molhada/umida/seca`). Caminha por
  `ctx.args` com as regras:
  - Token iniciando com `--`: inicia um nome de formulário (remove o prefixo).
  - `--name=valor`: completa o par inline.
  - Token sem prefixo `-`: é o valor do formulário pendente; se não houver
    pendente → `click.UsageError`.
  - Token iniciando com `-` (sem ser `--`): sem formulário pendente →
    `click.UsageError` (ex.: flag curto digitado errado); com formulário
    pendente → `click.UsageError` (valores começando com `-` não são
    suportados; caminhos e URLs não começam com `-`).
  - Nome normalizado: `strip('-').upper()` — preserva hífens
    (`--faro-seco` → `FARO-SECO`); `--sniff` continua `SNIFF`.
  - Nenhum formulário → `click.UsageError` (mantém o comportamento atual).
  - Nome duplicado → `click.UsageError` (erro explícito em vez de
    sobrescrever silenciosamente).
  - Valor vazio (flag no fim da linha, ex. `--sniff` como último token) →
    `click.UsageError`.

### `src/analizador_irrf/__init__.py`

- `main()`: remover params `sniff/molhada/umida/seca`; usar
  `@click.pass_context` e ler `ctx.args` via `coletar_arquivos_formulario`.
- Adicionar `context_settings=dict(allow_extra_args=True,
  ignore_unknown_options=True)` ao decorator `@click.command`.
- Atualizar docstring: documentar `--<name> <arquivo>` com exemplo
  (ex.: `irrf --nomes nomes.txt -a A1,A2 --sniff sniff.csv --faro-seco faro.csv`).

### `src/analizador_irrf/report.py`

- **Sem mudanças de lógica.** `TIPO_LABEL` mantém os rótulos dos nomes
  conhecidos (SNIFF→"Sniff", MOLHO→"Molhada", UMIDA→"Úmida", SECA→"Seca");
  nomes genéricos caem no fallback existente `TIPO_LABEL.get(t, t)`.
- `_ordenar_tipos` já produz o comportamento desejado: conhecidos primeiro na
  ordem fixa atual; desconhecidos depois, na ordem de aparição no comando
  (sort estável sobre a ordem de inserção do dict em `matcher.py`).

### `src/analizador_irrf/reader.py`

- **Remover** `extrair_tipo_formulario()` — código morto (não é chamado em
  lugar nenhum do source) e hardcoda os 4 tipos, agora desalinhado com nomes
  arbitrários. Remover também a importação/exportação em `__init__.py`
  (`__all__`).

### Sem mudanças

- `matcher.py` — pipeline já genérico (chaves do dict = colunas).
- `web.py` / `templates/form.html` — fora do escopo (decisão do usuário).

## Comportamento resultante

| Comando | Colunas no relatório |
|---|---|
| `--sniff a.csv` | Sniff |
| `--sniff a.csv --faro-seco b.csv` | Sniff, FARO-SECO |
| `--faro-seco b.csv --sniff a.csv` | Sniff, FARO-SECO (conhecidos primeiro) |
| nenhum formulário | UsageError |
| `--sniff a.csv --sniff b.csv` | UsageError (duplicado) |

## Verificação (aceite)

1. `irrf --help` renderiza com rich_click e documenta `--<name> <arquivo>`.
2. Backward compat: `--sniff sniff.csv` (com os outros flags fixos) gera a
   mesma tabela de antes.
3. Nome arbitrário: `--sniff a.csv --faro-seco b.csv` com CSVs de fixture
   gera colunas "Sniff" e "FARO-SECO" com os status ✓/✗ corretos.
4. Sem formulário → UsageError.
5. `--sniff a.csv --sniff b.csv` → UsageError (duplicado).
6. `--sniff` como último token (sem valor) → UsageError.
7. `--faro-seco=b.csv` (sintaxe `=`) funciona igual.
