from pathlib import Path
import json

from data_utils import (
    download_file,
    extract_zip,
    load_income_sectors,
    load_income_neighborhoods,
    load_sector_geometry,
    load_neighborhood_geometry,
    build_municipal_boundary,
    validate_downloads
)

# ============================================================
# CAMINHOS DO PROJETO
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = PROJECT_ROOT / "config.json"

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "ibge"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

STUDY_AREA = config["study_area"]
STUDY_AREA_CODE = config["study_area_code"]

UF = config["uf"]
CRS = config["crs"]

INCOME_VARIABLE = config["income_variable"]
INCOME_WEIGHT = config["income_weight"]


# ============================================================
# URLS
# ============================================================

URL_RENDA_SETORES = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/"
    "Agregados_por_setores_renda_responsavel_BR_20260508_csv.zip"
)

URL_MALHA_SETORES = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios/"
    "malha_com_atributos/setores/shp/UF/RS/"
    "RS_setores_CD2022.zip"
)

URL_MALHA_BAIRROS = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios/"
    "malha_com_atributos/bairros/shp/UF/RS/"
    "RS_bairros_CD2022.zip"
)

# Estes dois eu deixaria para preencher
# depois de confirmar os nomes exatos no FTP:
URL_RENDA_BAIRROS = None
URL_AGREGADOS_BASICOS = None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("DOWNLOAD E PREPARAÇÃO DOS DADOS DO CENSO 2022")
    print("=" * 70)

    print(f"Área de estudo: {STUDY_AREA}")
    print(f"Código IBGE: {STUDY_AREA_CODE}")
    print(f"UF: {UF}")
    print(f"CRS: {CRS}")
    print()


    # ========================================================
    # 1. RENDA POR SETOR
    # ========================================================

    renda_dir = RAW_DIR / "renda_setores"

    renda_zip = renda_dir / "renda_setores.zip"
    renda_extract = renda_dir / "extracted"

    renda_dir.mkdir(parents=True, exist_ok=True)

    download_file(
        url=URL_RENDA_SETORES,
        destination=renda_zip
    )

    extract_zip(
        zip_path=renda_zip,
        extract_dir=renda_extract
    )

    renda_setores = load_income_sectors(
        source_dir=renda_extract,
        municipality_code=STUDY_AREA_CODE,
        income_variable=INCOME_VARIABLE,
        income_weight=INCOME_WEIGHT,
    )

    output_renda_setores = (
        PROCESSED_DIR
        / "renda_setores_poa.csv"
    )

    renda_setores.to_csv(
        output_renda_setores,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"Renda por setor salva em: "
        f"{output_renda_setores}"
    )


    # ========================================================
    # 2. MALHA DE SETORES
    # ========================================================

    setores_dir = RAW_DIR / "setores"

    setores_zip = setores_dir / "setores_rs.zip"

    setores_dir.mkdir(parents=True, exist_ok=True)

    download_file(
        url=URL_MALHA_SETORES,
        destination=setores_zip
    )

    setores_poa = load_sector_geometry(
        zip_path=setores_zip,
        municipality_code=STUDY_AREA_CODE,
        target_crs=CRS,
    )


    # ========================================================
    # 3. JUNTA RENDA + GEOMETRIA
    # ========================================================

    setores_poa["CD_SETOR"] = (
        setores_poa["CD_SETOR"]
        .astype(str)
    )

    renda_setores["CD_SETOR"] = (
        renda_setores["CD_SETOR"]
        .astype(str)
    )

    setores_com_renda = setores_poa.merge(
        renda_setores,
        on="CD_SETOR",
        how="left",
        validate="one_to_one"
    )

    output_setores = (
        PROCESSED_DIR
        / "setores_poa.gpkg"
    )

    setores_com_renda.to_file(
        output_setores,
        layer="setores_poa",
        driver="GPKG"
    )

    print(
        f"Setores com renda salvos em: "
        f"{output_setores}"
    )


    # ========================================================
    # 4. MALHA DE BAIRROS
    # ========================================================

    bairros_dir = RAW_DIR / "bairros"

    bairros_zip = bairros_dir / "bairros_rs.zip"

    bairros_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    download_file(
        url=URL_MALHA_BAIRROS,
        destination=bairros_zip
    )

    bairros_poa = load_neighborhood_geometry(
        zip_path=bairros_zip,
        municipality_code=STUDY_AREA_CODE,
        target_crs=CRS,
    )

    output_bairros = (
        PROCESSED_DIR
        / "bairros_poa.gpkg"
    )

    bairros_poa.to_file(
        output_bairros,
        layer="bairros_poa",
        driver="GPKG"
    )

    print(
        f"Malha de bairros salva em: "
        f"{output_bairros}"
    )


    # ========================================================
    # 5. LIMITE MUNICIPAL
    # ========================================================

    limite_poa = build_municipal_boundary(
        setores_poa
    )

    output_limite = (
        PROCESSED_DIR
        / "limite_poa.gpkg"
    )

    limite_poa.to_file(
        output_limite,
        layer="limite_poa",
        driver="GPKG"
    )

    print(
        f"Limite municipal salvo em: "
        f"{output_limite}"
    )


    # ========================================================
    # 6. RENDA POR BAIRRO
    # ========================================================

    if URL_RENDA_BAIRROS is not None:

        renda_bairros_dir = (
            RAW_DIR
            / "renda_bairros"
        )

        renda_bairros_zip = (
            renda_bairros_dir
            / "renda_bairros.zip"
        )

        renda_bairros_extract = (
            renda_bairros_dir
            / "extracted"
        )

        renda_bairros_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        download_file(
            url=URL_RENDA_BAIRROS,
            destination=renda_bairros_zip
        )

        extract_zip(
            zip_path=renda_bairros_zip,
            extract_dir=renda_bairros_extract
        )

        renda_bairros = (
            load_income_neighborhoods(
                source_dir=renda_bairros_extract,
                municipality_code=STUDY_AREA_CODE,
                income_variable=INCOME_VARIABLE,
                income_weight=INCOME_WEIGHT,
            )
        )

        output_renda_bairros = (
            PROCESSED_DIR
            / "renda_bairros_poa.csv"
        )

        renda_bairros.to_csv(
            output_renda_bairros,
            index=False,
            encoding="utf-8-sig"
        )

        print(
            f"Renda por bairro salva em: "
            f"{output_renda_bairros}"
        )

    else:

        print(
            "\nRenda por bairro: URL ainda não definida."
        )


    # ========================================================
    # 7. AGREGADOS BÁSICOS
    # ========================================================

    if URL_AGREGADOS_BASICOS is not None:

        print(
            "\nDownload dos agregados básicos "
            "será executado aqui."
        )

    else:

        print(
            "\nAgregados básicos: URL ainda "
            "não definida."
        )


    # ========================================================
    # 8. VALIDAÇÃO FINAL
    # ========================================================

    validate_downloads(
        setores=setores_com_renda,
        bairros=bairros_poa,
        limite=limite_poa,
        income_variable=INCOME_VARIABLE,
    )


    print()
    print("=" * 70)
    print("PIPELINE FINALIZADO")
    print("=" * 70)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()
