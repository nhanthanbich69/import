import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Tạo File Import", layout="wide")
st.title("📦 Tạo File Import (Chuẩn ERP)")

# ================= CORE =================
def clean(df):
    df.columns = df.columns.str.strip()
    return df


# ===== MAP ĐƠN VỊ (2 KEY như XLOOKUP) =====
def map_dvtinh(df, df_dv):
    if df_dv.empty:
        return [""] * len(df)

    df1 = df.copy()
    df2 = df_dv.copy()

    for col in ["Đơn vị lẻ", "Đơn vị lớn"]:
        df1[col] = df1[col].astype(str).str.lower().str.strip()
        df2[col] = df2[col].astype(str).str.lower().str.strip()

    df_merge = df1.merge(
        df2,
        on=["Đơn vị lẻ", "Đơn vị lớn"],
        how="left"
    )

    return df_merge.get("Mã", "")


# ===== MAP VAT =====
def map_vat(val):
    if pd.isna(val):
        return "0002"  # default 10%

    val = str(val).replace("%", "").strip()

    try:
        v = float(val)
    except:
        return "0002"

    if v == 0:
        return "0001"
    elif v == 5:
        return "0003"
    elif v == 8:
        return "0006"
    else:
        return "0002"


# ===== BUILD =====
def build(df, template_cols, df_dv):
    df = df.copy()

    # ===== CLEAN PRICE =====
    price_cols = [
        "Giá bán có thuế",
        "Giá bán thùng có thuế",
        "Giá mua chưa thuế"
    ]

    for col in price_cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", "")
                .replace("", "0")
                .astype(float)
            )

    VAT = 1.1

    # ===== BUILD RESULT =====
    result = pd.DataFrame(columns=template_cols)

    # ===== BASIC =====
    result["Mahangcuancc"] = df.get("Mã hàng NCC")
    result["Masieuthi"] = ""  # để trống

    result["Madonvi"] = "0001"
    result["Manganh"] = df.get("Ngành hàng", "")
    result["Manhomhang"] = df.get("Nhóm hàng", "")

    result["Trangthaikd"] = 1

    result["Quycach"] = df.get("Quy cách", "")
    result["Quycachmax"] = df.get("Quy cách max", 1)

    result["Tendaydu"] = df.get("Tên sản phẩm", "")
    result["Tenviettat"] = result["Tendaydu"]

    # ===== ĐƠN VỊ TÍNH =====
    result["Madvtinh"] = map_dvtinh(df, df_dv)

    result["Makhachhang"] = ""

    # ===== VAT =====
    vat_source = df.get("Mã VAT mua", df.get("VAT mua", 10))
    result["Mavatmua"] = vat_source.apply(map_vat)
    result["Mavatban"] = "0001"

    # ===== GIÁ =====
    giaban_le = df.get("Giá bán có thuế", 0)
    giaban_thung = df.get("Giá bán thùng có thuế", giaban_le)
    giamua = df.get("Giá mua chưa thuế", 0)

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

    # ===== CÁC CỘT KHÁC =====
    for col in template_cols:
        if col not in result.columns:
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


# ===== TAB 2 =====
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
