package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"strconv"
)

// Nutrientes mapeia o nome do nutriente ao seu valor
type Nutrientes map[string]float64

// Alimento representa uma linha da sua tabela
type Alimento struct {
	Nome        string
	Categoria   string
	PorcaoMedia float64
	Composicao  Nutrientes // Valores por 100g
}

// DataStore guarda todo o contexto do TSV na memória
type DataStore struct {
	Unidades    map[string]string
	Recomendado Nutrientes
	Maximo      Nutrientes
	Prioridades Nutrientes // A sua nova linha 4 (1=Necessário, 2=Desejável, etc)
	Alimentos   []Alimento
	Colunas     []string // Guardar a ordem das colunas para os loops
}

// Função para ler o TSV - O motor bruto que substitui o "pd.read_csv"
func carregarDados(caminho string) (*DataStore, error) {
	file, err := os.Open(caminho)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.Comma = '\t' // Especificando que é um TSV

	linhas, err := reader.ReadAll()
	if err != nil {
		return nil, err
	}

	if len(linhas) < 5 { // Cabeçalho + 4 linhas de metadados mínimas
		return nil, fmt.Errorf("o arquivo não tem a estrutura mínima de cabeçalhos")
	}

	cabecalho := linhas[0]
	unidadesStr := linhas[1]
	recomendadoStr := linhas[2]
	maximoStr := linhas[3]
	prioridadeStr := linhas[4] // A nova linha que você vai criar no TSV

	store := &DataStore{
		Unidades:    make(map[string]string),
		Recomendado: make(Nutrientes),
		Maximo:      make(Nutrientes),
		Prioridades: make(Nutrientes),
		Alimentos:   []Alimento{},
		Colunas:     []string{},
	}

	// Isolando apenas as colunas numéricas de nutrientes
	// Assumindo: [0]Nome, [1]Categoria, [2]Porção Média, [3...] Nutrientes
	inicioNutrientes := 3
	for i := inicioNutrientes; i < len(cabecalho); i++ {
		nutriente := cabecalho[i]
		store.Colunas = append(store.Colunas, nutriente)

		store.Unidades[nutriente] = unidadesStr[i]
		store.Recomendado[nutriente], _ = strconv.ParseFloat(recomendadoStr[i], 64)
		store.Maximo[nutriente], _ = strconv.ParseFloat(maximoStr[i], 64)
		store.Prioridades[nutriente], _ = strconv.ParseFloat(prioridadeStr[i], 64)
	}

	// Da linha 5 em diante são os alimentos
	for i := 5; i < len(linhas); i++ {
		linha := linhas[i]
		if len(linha) == 0 || linha[0] == "" {
			continue // Pula linhas vazias
		}

		porcaoMedia, _ := strconv.ParseFloat(linha[2], 64)

		alimento := Alimento{
			Nome:        linha[0],
			Categoria:   linha[1],
			PorcaoMedia: porcaoMedia,
			Composicao:  make(Nutrientes),
		}

		for j := inicioNutrientes; j < len(cabecalho) && j < len(linha); j++ {
			nutriente := cabecalho[j]
			val, err := strconv.ParseFloat(linha[j], 64)
			if err != nil {
				val = 0 // Trata campos vazios/erros como zero
			}
			alimento.Composicao[nutriente] = val
		}

		store.Alimentos = append(store.Alimentos, alimento)
	}

	return store, nil
}

func main() {
	// Apenas para testar se o parser funciona antes de montar o TUI
	store, err := carregarDados("database.tsv")
	if err != nil {
		log.Fatalf("Erro ao carregar dados: %v", err)
	}

	fmt.Printf("Sucesso! Carregados %d alimentos.\n", len(store.Alimentos))
	if len(store.Alimentos) > 0 {
		primeiro := store.Alimentos[0]
		fmt.Printf("Exemplo - %s (Porção: %.1fg, Vit C: %.2f %s)\n",
			primeiro.Nome, primeiro.PorcaoMedia,
			primeiro.Composicao["C"], store.Unidades["C"])
	}
}
