import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Tạo File Import", layout="wide")
st.title("📦 Tạo File Import (Python xử lý)")

# ================= CORE =================
def clean(df):
    df.columns = df.columns.str.strip()
    return df


# ===== MAP ĐƠN VỊ =====
def map_dvtinh(df, df_dv):
    if df_dv.empty:
        return pd.Series([""] * len(df))

    df1 = df.copy()
    df2 = df_dv.copy()

    for col in ["Đơn vị lẻ", "Đơn vị lớn"]:
        if col in df1.columns:
            df1[col] = df1[col].astype(str).str.lower().str.strip()
        if col in df2.columns:
            df2[col] = df2[col].astype(str).str.lower().str.strip()

    # merge 2 key
    df_merge = df1.merge(df2, on=["Đơn vị lẻ", "Đơn vị lớn"], how="left")

    madv = df_merge["Mã"] if "Mã" in df_merge.columns else pd.Series([None]*len(df))

    # fallback theo 1 key
    mask = madv.isna()
    if mask.any():
        df_fb = df1[mask].merge(df2, on=["Đơn vị lẻ"], how="left")
        if "Mã" in df_fb.columns:
            madv.loc[mask] = df_fb["Mã"].values

    return madv.fillna("")


# ===== MAP VAT =====
def map_vat_series(series):
    def _map(v):
        if pd.isna(v):
            return "0002"
        try:
            x = float(str(v).replace("%", "").strip())
        except:
            return "0002"

        if x == 0:
            return "0001"
        elif x == 5:
            return "0003"
        elif x == 8:
            return "0006"
        else:
            return "0002"

    return series.apply(_map)


# ===== CLEAN NUMBER =====
def to_number(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .replace("", "0")
                .astype(float)
            )
    return df


# ===== BUILD =====
def build(df, template_cols, df_dv):
    df = df.copy()

    # ===== CLEAN PRICE =====
    df = to_number(df, [
        "Giá bán có thuế",
        "Giá bán thùng có thuế",
        "Giá mua chưa thuế"
    ])

    VAT = 1.1

    result = pd.DataFrame(index=df.index)

    # ===== BASIC =====
    result["Mahangcuancc"] = df.get("Mã hàng NCC")
    result["Masieuthi"] = ""

    result["Madonvi"] = "0001"
    result["Manganh"] = df.get("Ngành hàng", "")
    result["Manhomhang"] = df.get("Nhóm hàng", "")

    result["Trangthaikd"] = 1

    result["Quycach"] = df.get("Quy cách", "")
    result["Quycachmax"] = df.get("Quy cách max", 1)

    result["Tendaydu"] = df.get("Tên sản phẩm", "")
    result["Tenviettat"] = result["Tendaydu"]

    # ===== ĐƠN VỊ =====
    result["Madvtinh"] = map_dvtinh(df, df_dv)

    result["Makhachhang"] = ""

    # ===== VAT =====
    if "Mã VAT mua" in df.columns:
        vat_series = df["Mã VAT mua"]
    elif "VAT mua" in df.columns:
        vat_series = df["VAT mua"]
    else:
        vat_series = pd.Series([10]*len(df))

    result["Mavatmua"] = map_vat_series(vat_series)
    result["Mavatban"] = "0001"

    # ===== GIÁ =====
    giaban_le = df["Giá bán có thuế"] if "Giá bán có thuế" in df.columns else pd.Series([0]*len(df))
    giaban_thung = df["Giá bán thùng có thuế"] if "Giá bán thùng có thuế" in df.columns else giaban_le
    giamua = df["Giá mua chưa thuế"] if "Giá mua chưa thuế" in df.columns else pd.Series([0]*len(df))

    result["Giabanlecovat"] = giaban_le
    result["Giabanbuoncovat"] = giaban_thung

    result["Giabanlechuavat"] = giaban_le / VAT
    result["Giabanbuonchuavat"] = giaban_thung / VAT

    result["Giamuacovat"] = giamua * VAT
    result["Giamuachuavat"] = giamua

    result["Giathungbuonchuavat"] = giaban_thung / VAT
    result["Giathungbuoncovat"] = giaban_thung

    result["Gialecodinh"] = giaban_le
    result["Giathungcodinh"] = giaban_thung

    # ===== FILL CỘT THEO TEMPLATE =====
    final = pd.DataFrame(columns=template_cols)

    for col in template_cols:
        if col in result.columns:
            final[col] = result[col]
        else:
            final[col] = ""

    return final


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# ================= UI =================
tab1, tab2 = st.tabs(["📥 Xử lý", "📊 Kết quả"])

with tab1:
    file_source = st.file_uploader("📄 File danh mục NPP", type=["xlsx"])
    file_dv = st.file_uploader("📄 File đơn vị tính", type=["xlsx"])
    file_template = st.file_uploader("📄 File template", type=["xlsx"])

    if st.button("🚀 Xử lý"):
        if not file_source or not file_template:
            st.error("Thiếu file")
        else:
            try:
                df = clean(pd.read_excel(file_source))
                template = clean(pd.read_excel(file_template))

                df_dv = pd.DataFrame()
                if file_dv:
                    df_dv = clean(pd.read_excel(file_dv))

                result = build(df, template.columns, df_dv)

                st.session_state["result"] = result
                st.success(f"✅ {len(result)} dòng")

            except Exception as e:
                st.error(e)


with tab2:
    if "result" in st.session_state:
        df = st.session_state["result"]

        keyword = st.text_input("🔍 Tìm nhanh")

        if keyword:
            df = df[df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)]

        st.dataframe(df, use_container_width=True)

        st.download_button(
            "📥 Tải Excel",
            data=to_excel(df),
            file_name="import.xlsx"
        )
    else:
        st.info("Chưa có dữ liệu")
