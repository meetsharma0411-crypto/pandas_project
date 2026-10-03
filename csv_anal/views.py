from django.shortcuts import render
from django.http import HttpResponse
import pandas as pd
import plotly.express as px
import json


def read_file(uploaded_file):

    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)

    elif name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)

    elif name.endswith(".xls"):
        df = pd.read_excel(uploaded_file)

    elif name.endswith(".json"):
        df = pd.read_json(uploaded_file)

    else:
        raise ValueError(
            "Only CSV, XLSX, XLS and JSON files are supported."
        )

    return df


def clean_data(df):

    # Remove duplicate rows
    df = df.drop_duplicates()

    # Clean column names
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace(" ", "_")
    )

    # Process missing values
    for column in df.columns:

        if df[column].isnull().sum() > 0:

            # Numeric column
            if pd.api.types.is_numeric_dtype(df[column]):

                median_value = df[column].median()

                df[column] = df[column].fillna(median_value)

            # Datetime column
            elif pd.api.types.is_datetime64_any_dtype(df[column]):

                df[column] = df[column].ffill().bfill()

            # Text / categorical column
            else:

                mode_value = df[column].mode()

                if len(mode_value) > 0:
                    df[column] = df[column].fillna(mode_value[0])
                else:
                    df[column] = df[column].fillna("Unknown")

    return df


def home(request):

    context = {
        "uploaded": False,
        "chart_json": None,
    }

    # -------------------------
    # FILE UPLOAD
    # -------------------------

    if request.method == "POST" and request.FILES.get("data_file"):

        uploaded_file = request.FILES["data_file"]

        try:

            df = read_file(uploaded_file)

            original_rows = len(df)

            missing_before = int(df.isnull().sum().sum())

            duplicate_count = int(df.duplicated().sum())

            # Clean data
            df = clean_data(df)

            missing_after = int(df.isnull().sum().sum())

            # Column types
            numeric_columns = list(
                df.select_dtypes(include="number").columns
            )

            categorical_columns = list(
                df.select_dtypes(
                    include=["object", "category", "bool"]
                ).columns
            )

            datetime_columns = list(
                df.select_dtypes(
                    include=["datetime"]
                ).columns
            )

            # Statistics
            statistics = {}

            for column in df.columns:

                if pd.api.types.is_numeric_dtype(df[column]):

                    statistics[column] = {
                        "type": "Numeric",
                        "count": int(df[column].count()),
                        "unique": int(df[column].nunique()),
                        "mean": round(float(df[column].mean()), 2),
                        "median": round(float(df[column].median()), 2),
                        "min": round(float(df[column].min()), 2),
                        "max": round(float(df[column].max()), 2),
                        "std": round(float(df[column].std()), 2),
                    }

                else:

                    statistics[column] = {
                        "type": "Categorical",
                        "count": int(df[column].count()),
                        "unique": int(df[column].nunique()),
                        "mode": str(df[column].mode().iloc[0])
                        if not df[column].mode().empty
                        else "N/A",
                    }

            # Preview
            preview = df.head(10).to_html(
                classes="data-table",
                index=False,
                border=0
            )

            context.update({
                "uploaded": True,
                "filename": uploaded_file.name,
                "rows": len(df),
                "columns": len(df.columns),
                "original_rows": original_rows,
                "duplicates": duplicate_count,
                "missing_before": missing_before,
                "missing_after": missing_after,
                "column_names": list(df.columns),
                "numeric_columns": numeric_columns,
                "categorical_columns": categorical_columns,
                "datetime_columns": datetime_columns,
                "statistics": statistics,
                "preview": preview,
            })

            # Save dataframe temporarily in session
            request.session["data"] = df.to_json()

        except Exception as e:

            context["error"] = str(e)

    # -------------------------
    # VISUALIZATION
    # -------------------------

    if request.method == "POST" and request.POST.get("chart_type"):

        try:

            data_json = request.session.get("data")

            if not data_json:
                context["error"] = "Please upload a file first."
                return render(
                    request,
                    "csv_anal/home.html",
                    context
                )

            df = pd.read_json(data_json)

            chart_type = request.POST.get("chart_type")
            x_column = request.POST.get("x_column")
            y_column = request.POST.get("y_column")

            fig = None

            # Histogram
            if chart_type == "histogram":

                fig = px.histogram(
                    df,
                    x=x_column,
                    title=f"Histogram - {x_column}"
                )

            # Scatter
            elif chart_type == "scatter":

                fig = px.scatter(
                    df,
                    x=x_column,
                    y=y_column,
                    title=f"{x_column} vs {y_column}"
                )

            # Line
            elif chart_type == "line":

                fig = px.line(
                    df,
                    x=x_column,
                    y=y_column,
                    title=f"{y_column} over {x_column}"
                )

            # Bar
            elif chart_type == "bar":

                fig = px.bar(
                    df,
                    x=x_column,
                    y=y_column,
                    title=f"{y_column} by {x_column}"
                )

            # Box
            elif chart_type == "box":

                fig = px.box(
                    df,
                    y=y_column,
                    title=f"Box Plot - {y_column}"
                )

            # Pie
            elif chart_type == "pie":

                counts = df[x_column].value_counts().reset_index()

                counts.columns = [
                    x_column,
                    "count"
                ]

                fig = px.pie(
                    counts,
                    names=x_column,
                    values="count",
                    title=f"Distribution of {x_column}"
                )

            # Correlation Heatmap
            elif chart_type == "heatmap":

                correlation = df.select_dtypes(
                    include="number"
                ).corr()

                fig = px.imshow(
                    correlation,
                    text_auto=True,
                    title="Correlation Heatmap"
                )

            if fig:

                fig.update_layout(
                    height=600
                )

                context["chart_json"] = fig.to_json()

        except Exception as e:

            context["error"] = str(e)

    return render(
        request,
        "csv_anal/home.html",
        context
    )