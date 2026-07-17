import pandas as pd
from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Input,
    Button,
    Label,
    TabbedContent,
    TabPane,
    Select,
    TextArea,
)

from textual.containers import Horizontal, Vertical


class NutreeApp(App):
    TITLE = "Nutree - Análise Nutricional"

    CSS = """
    #top-config {
        layout: horizontal;
        height: auto;
        margin-bottom: 1;
    }
    #nutriente_select {
        width: 3fr;
        margin-right: 1;
    }
    #top_n_input {
        width: 1fr;
    }
    #calc_input {
        height: 10;
        margin-bottom: 1;
        border: solid green;
    }
    #btn_calcular {
        margin-bottom: 1;
    }
    .metrics-box {
        height: auto;
        padding-bottom: 1;
        content-align: center middle;
    }
    #lbl_recomendado {
        margin-right: 4;
        color: $success;
    }
    #lbl_maximo {
        color: $error;
    }
    """

    def __init__(self):
        super().__init__()
        self.df_foods = None
        self.unidades = None

    def on_mount(self) -> None:
        # Paga o "pedágio" do Pandas apenas uma vez aqui
        self.load_data()

        # Configura as tabelas e opções
        self.configurar_interface()

    def load_data(self) -> None:
        try:
            df_raw = pd.read_csv("TabelaNutricional.tsv", sep="\t")

            self.unidades = df_raw.iloc[0]
            self.recomendado = df_raw.iloc[1]
            self.maximo = df_raw.iloc[2]

            self.df_foods = df_raw.iloc[3:].copy()

            # Garante que as novas colunas de metadados não sejam forçadas a números
            colunas_ignorar = ["Nome", "Categoria", "Porção Média"]
            cols_numericas = [
                c for c in self.df_foods.columns if c not in colunas_ignorar
            ]

            for col in cols_numericas:
                self.df_foods[col] = pd.to_numeric(
                    self.df_foods[col], errors="coerce"
                ).fillna(0)

        except Exception as e:
            self.exit(f"Erro ao carregar TabelaNutricional.tsv: {e}")

    def configurar_interface(self) -> None:
        # Preenche o Select com a lista de nutrientes (ignorando o 'Nome')
        select = self.query_one("#nutriente_select", Select)
        colunas = list(self.df_foods.columns.drop("Nome"))
        select.set_options([(col, col) for col in colunas])

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            # ABA 1: Ranking de Nutrientes
            with TabPane("Top Nutrientes", id="tab-top"):
                with Horizontal(id="top-config"):
                    yield Select(
                        [], prompt="Selecione o nutriente...", id="nutriente_select"
                    )
                    yield Input(
                        value="5", placeholder="Top N", id="top_n_input", type="integer"
                    )
                    with Horizontal(id="top-metrics", classes="metrics-box"):
                        yield Label("", id="lbl_recomendado")
                        yield Label("", id="lbl_maximo")
                yield DataTable(id="top_table", cursor_type="row")

            # ABA 2: Calculadora de Refeição
            with TabPane("Calculadora de Refeição", id="tab-calc"):
                yield Label(
                    "Insira os alimentos (Formato -> Nome: Gramas). Um por linha:"
                )
                yield TextArea(
                    "Ovos: 150\nPeito de Frango: 200\nAzeite: 15", id="calc_input"
                )
                yield Button("Calcular Totais", id="btn_calcular", variant="success")
                yield DataTable(id="calc_table", cursor_type="row")
        yield Footer()

    # --- EVENTOS DA ABA 1 (TOP N) ---
    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "nutriente_select":
            self.atualizar_top_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "top_n_input":
            self.atualizar_top_table()

    def atualizar_top_table(self) -> None:
        table = self.query_one("#top_table", DataTable)
        lbl_rec = self.query_one("#lbl_recomendado", Label)
        lbl_max = self.query_one("#lbl_maximo", Label)

        table.clear(columns=True)
        lbl_rec.update("")
        lbl_max.update("")

        select = self.query_one("#nutriente_select", Select)
        n_input = self.query_one("#top_n_input", Input)

        nutriente = select.value

        if not isinstance(nutriente, str) or nutriente not in self.df_foods.columns:
            return

        try:
            n = int(n_input.value) if n_input.value else 5
        except ValueError:
            n = 5

        unidade = self.unidades[nutriente]

        # --- ATUALIZA AS MÉTRICAS DE SEGURANÇA ---
        val_rec = self.recomendado[nutriente]
        val_max = self.maximo[nutriente]

        # Limpa eventuais "NaN" do Pandas caso a célula original estivesse vazia
        str_rec = (
            f"{val_rec}" if pd.notna(val_rec) and str(val_rec).strip() != "" else "N/A"
        )
        str_max = (
            f"{val_max}" if pd.notna(val_max) and str(val_max).strip() != "" else "N/A"
        )

        lbl_rec.update(f"🎯 Alvo Diário: [b]{str_rec} {unidade}[/b]")
        lbl_max.update(f"⚠️ Teto (UL): [b]{str_max} {unidade}[/b]")
        # -----------------------------------------

        table.add_columns("Pos", "Alimento", f"Qtd ({unidade})")

        top_df = (
            self.df_foods[["Nome", nutriente]]
            .sort_values(by=nutriente, ascending=False)
            .head(n)
        )

        for i, (_, row) in enumerate(top_df.iterrows(), 1):
            table.add_row(str(i), row["Nome"], f"{row[nutriente]}")

    # --- EVENTOS DA ABA 2 (CALCULADORA) ---
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_calcular":
            self.atualizar_calc_table()

    def atualizar_calc_table(self) -> None:
        text_area = self.query_one("#calc_input", TextArea)
        table = self.query_one("#calc_table", DataTable)
        table.clear(columns=True)

        linhas = text_area.text.strip().split("\n")
        dieta = {}
        for linha in linhas:
            if not linha.strip():
                continue
            parts = linha.split(":")
            if len(parts) == 2:
                nome = parts[0].strip()
                try:
                    qtd = float(parts[1].strip())
                    dieta[nome] = qtd
                except ValueError:
                    pass

        totais = pd.Series(dtype=float)
        colunas_ignorar = ["Nome", "Categoria", "Porção Média"]

        for alimento, qtd in dieta.items():
            linha_df = self.df_foods[self.df_foods["Nome"] == alimento]
            if not linha_df.empty:
                # Isola apenas as colunas de nutrientes para o cálculo matemático
                cols_calc = [c for c in linha_df.columns if c not in colunas_ignorar]
                valores_100g = linha_df[cols_calc].iloc[0]

                proporcao = pd.to_numeric(valores_100g, errors="coerce").fillna(0) * (
                    qtd / 100.0
                )

                if totais.empty:
                    totais = proporcao
                else:
                    totais = totais.add(proporcao, fill_value=0)

        if totais.empty:
            table.add_columns("Erro")
            table.add_row("Nenhum alimento válido foi processado.")
            return

        # Adiciona as colunas de contexto solicitadas
        table.add_columns(
            "Nutriente", "Total Ingerido", "Alvo Diário", "Máximo (UL)", "Unidade"
        )

        totais_limpos = totais[totais > 0].sort_values(ascending=False)
        for nutriente, valor in totais_limpos.items():
            unid = str(self.unidades.get(nutriente, ""))

            # Busca os limites no cabeçalho
            val_rec = self.recomendado.get(nutriente, "")
            val_max = self.maximo.get(nutriente, "")

            # Formata para evitar exibição de "nan" (not a number) na interface
            str_rec = (
                str(val_rec)
                if pd.notna(val_rec) and str(val_rec).strip() != ""
                else "-"
            )
            str_max = (
                str(val_max)
                if pd.notna(val_max) and str(val_max).strip() != ""
                else "-"
            )

            table.add_row(nutriente, f"{valor:.2f}", str_rec, str_max, unid)


if __name__ == "__main__":
    app = NutreeApp()
    app.run()
