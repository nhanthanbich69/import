import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Tạo File Import", layout="wide")
st.title("📦 Tạo File Import (Pro Version)")

# ================= FUNCTIONS =================
def clean_text(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.lower().str.strip()
    return df


def build_from_template(df_source, df_template, mapping, df_don_vi):
    # merge đơn vị
    if "Đơn vị lẻ" in df_source.columns and "Đơn vị tính" in df_don_vi.columns:
        df_source = df_source.merge(
            df_don_vi,
            left_on="Đơn vị lẻ",
            right_on="Đơn vị tính",
            how="left"
        )

    result = pd.DataFrame(columns=df_template.columns)

    for col in result.columns:
        if col in mapping:
            source_col = mapping[col]
            if source_col in df_source.columns:
                result[col] = df_source[source_col]
            else:
                result[col] = ""
        else:
            result[col] = ""

    # fix cứng
    if "Quycachmax" in result.columns:
        result["Quycachmax"] = 1

    if "Trangthaikd" in result.columns:
        result["Trangthaikd"] = 1

    if "Madonvi" in result.columns and "Mã đơn vị tính" in df_source.columns:
        result["Madonvi"] = df_source["Mã đơn vị tính"]

    return result


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# ================= UI =================
tab1, tab2 = st.tabs(["📥 Upload & Xử lý", "📊 Kết quả"])

# ================= TAB 1 =================
with tab1:
    st.header("Upload file")

    file_source = st.file_uploader("📄 File dữ liệu (NPP)", type=["xlsx"])
    file_don_vi = st.file_uploader("📄 File đơn vị", type=["xlsx"])
    file_template = st.file_uploader("📄 File template import", type=["xlsx"])

    st.subheader("⚙️ Mapping (Template → Source)")

    sample_mapping = {
        "Mahangcuancc": "Mã hàng NCC",
        "Tendaydu": "Tên sản phẩm",
        "Tenviettat": "Tên sản phẩm",
        "Quycach": "Quy cách",
        "Mavatnk": "Mã VAT mua"
    }

    mapping = {}
    for k, v in sample_mapping.items():
        mapping[k] = st.text_input(k, value=v)

    if st.button("🚀 Xử lý"):
        if not file_source or not file_template:
            st.error("Thiếu file 😑")
        else:
            try:
                df_source = pd.read_excel(file_source)
                df_template = pd.read_excel(file_template)

                df_source.columns = df_source.columns.str.strip()
                df_template.columns = df_template.columns.str.strip()

                if file_don_vi:
                    df_don_vi = pd.read_excel(file_don_vi)
                    df_don_vi.columns = df_don_vi.columns.str.strip()
                    df_don_vi = clean_text(df_don_vi, ["Đơn vị tính"])
                    df_source = clean_text(df_source, ["Đơn vị lẻ"])
                else:
                    df_don_vi = pd.DataFrame()

                result = build_from_template(
                    df_source,
                    df_template,
                    mapping,
                    df_don_vi
                )

                st.session_state["result"] = result

                st.success(f"✅ OK {len(result)} dòng")

            except Exception as e:
                st.error(f"Lỗi: {e}")


# ================= TAB 2 =================
with tab2:
    st.header("Kết quả")

    if "result" in st.session_state:
        df = st.session_state["result"]

        # ===== FILTER UI =====
        st.subheader("🔍 Lọc nhanh")

        col1, col2 = st.columns(2)

        with col1:
            selected_col = st.selectbox("Chọn cột", df.columns)

        with col2:
            keyword = st.text_input("Từ khoá")

        df_view = df.copy()

        if keyword:
            df_view = df_view[
                df_view[selected_col].astype(str).str.contains(keyword, case=False, na=False)
            ]

        # ===== ADVANCED FILTER =====
        st.subheader("🧠 Lọc nâng cao (query)")

        query_text = st.text_input(
            "Nhập query pandas",
            placeholder="Ví dụ: Madonvi.isna() hoặc Mahangcuancc == 'ABC123'"
        )

        if query_text:
            try:
                df_view = df_view.query(query_text)
            except Exception as e:
                st.error(f"Lỗi query: {e}")

        # ===== HIGHLIGHT ERROR =====
        st.subheader("⚠️ Dòng lỗi (thiếu đơn vị)")

        error_df = df[df["Madonvi"].isna()] if "Madonvi" in df.columns else pd.DataFrame()

        if not error_df.empty:
            st.warning(f"Có {len(error_df)} dòng lỗi")
            st.dataframe(error_df, use_container_width=True)
        else:
            st.success("Không có lỗi 🎉")

        # ===== DATA VIEW =====
        st.subheader("📊 Preview dữ liệu")
        st.dataframe(df_view, use_container_width=True)

        # ===== DOWNLOAD =====
        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                "📥 Tải file (đã lọc)",
                data=to_excel(df_view),
                file_name="import_filtered.xlsx"
            )

        with col2:
            st.download_button(
                "📥 Tải file (full)",
                data=to_excel(df),
                file_name="import_full.xlsx"
            )

    else:
        st.info("Chưa có dữ liệu")
