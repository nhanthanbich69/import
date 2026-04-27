import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Tạo File Import", layout="wide")
st.title("📦 Tạo File Import")

# ================= CORE =================
def clean(df):
    df.columns = df.columns.str.strip()
    return df


def map_don_vi(df, df_don_vi):
    if df_don_vi.empty:
        df["Madonvi"] = "CAI"
        return df

    # clean text
    for col in ["Đơn vị lẻ", "Đơn vị lớn"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().str.strip()

    for col in ["Đơn vị lẻ", "Đơn vị lớn"]:
        if col in df_don_vi.columns:
            df_don_vi[col] = df_don_vi[col].astype(str).str.lower().str.strip()

    # ===== merge 2 key =====
    df_merge = df.merge(
        df_don_vi,
        on=["Đơn vị lẻ", "Đơn vị lớn"],
        how="left"
    )

    if "Mã" in df_merge.columns:
        df["Madonvi"] = df_merge["Mã"]
    else:
        df["Madonvi"] = None

    # ===== fallback 1 key =====
    mask = df["Madonvi"].isna()

    if mask.any():
        df_fallback = df[mask].merge(
            df_don_vi,
            on=["Đơn vị lẻ"],
            how="left"
        )

        if "Mã" in df_fallback.columns:
            df.loc[mask, "Madonvi"] = df_fallback["Mã"].values

    # ===== default =====
    df["Madonvi"] = df["Madonvi"].fillna("CAI")

    return df


def build(df_source, df_template, df_don_vi):
    df = df_source.copy()

    # ===== KEY =====
    df["Mahangcuancc"] = df.get("Mã hàng NCC")
    df["Mahangcuancc"] = df["Mahangcuancc"].fillna(
        "AUTO_" + df.index.astype(str)
    )

    df["Masieuthi"] = df["Mahangcuancc"]

    # ===== NAME =====
    df["Tendaydu"] = df.get("Tên sản phẩm", "")
    df["Tenviettat"] = df["Tendaydu"].astype(str).str[:50]

    # ===== VAT =====
    df["Mavatnk"] = df.get("Mã VAT mua", "VAT10").fillna("VAT10")

    # ===== QUYCACH =====
    if "Quy cách" in df.columns:
        df["Quycach"] = df["Quy cách"]
    else:
        df["Quycach"] = df.get("Đơn vị lớn", "") + " x 1"

    df["Quycachmax"] = 1

    # ===== MAP ĐƠN VỊ (QUAN TRỌNG) =====
    df = map_don_vi(df, df_don_vi)

    # ===== STATUS =====
    df["Trangthaikd"] = 1

    # ===== BUILD THEO TEMPLATE =====
    result = pd.DataFrame(columns=df_template.columns)

    for col in result.columns:
        if col in df.columns:
            result[col] = df[col]
        else:
            result[col] = ""

    return result


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# ================= UI =================
tab1, tab2 = st.tabs(["📥 Xử lý", "📊 Kết quả"])

# ===== TAB 1 =====
with tab1:
    file_source = st.file_uploader("📄 File dữ liệu NPP", type=["xlsx"])
    file_don_vi = st.file_uploader("📄 File mapping đơn vị", type=["xlsx"])
    file_template = st.file_uploader("📄 File template import", type=["xlsx"])

    if st.button("🚀 Xử lý"):
        if not file_source or not file_template:
            st.error("Thiếu file")
        else:
            try:
                df_source = clean(pd.read_excel(file_source))
                df_template = clean(pd.read_excel(file_template))

                df_don_vi = pd.DataFrame()
                if file_don_vi:
                    df_don_vi = clean(pd.read_excel(file_don_vi))

                result = build(df_source, df_template, df_don_vi)

                st.session_state["result"] = result
                st.success(f"✅ {len(result)} dòng")

            except Exception as e:
                st.error(e)


# ===== TAB 2 =====
with tab2:
    if "result" in st.session_state:
        df = st.session_state["result"]

        # ===== FILTER =====
        col1, col2 = st.columns(2)

        with col1:
            col = st.selectbox("Chọn cột", df.columns)

        with col2:
            keyword = st.text_input("Tìm kiếm")

        df_view = df.copy()

        if keyword:
            df_view = df_view[
                df_view[col].astype(str).str.contains(keyword, case=False, na=False)
            ]

        # ===== ERROR CHECK =====
        if "Madonvi" in df.columns:
            err = df[df["Madonvi"] == "CAI"]
            if len(err) > 0:
                st.warning(f"⚠️ {len(err)} dòng không map được đơn vị (đang dùng CAI)")

        # ===== VIEW =====
        st.dataframe(df_view, use_container_width=True)

        # ===== DOWNLOAD =====
        st.download_button(
            "📥 Tải file Excel",
            data=to_excel(df_view),
            file_name="import.xlsx"
        )

    else:
        st.info("Chưa có dữ liệu")
