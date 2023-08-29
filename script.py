import os

import streamlit as st
from pycognaize.document import Document
import table_analysis

# Set page configuration
st.set_page_config(
    page_title="Document Fetcher",
    page_icon="📄",
    layout="wide"
)

def main():
    st.title("Document Fetcher")
    st.markdown("Enter the Recipe ID and Document ID below:")
    # Input fields for Recipe ID and Document ID
    API_HOST = st.text_input("API Host", value="https://gulfim-api.cognaize.com")
    x_auth_token = st.text_input("X Auth Token")

    os.environ['API_HOST'] = API_HOST
    os.environ['X_AUTH_TOKEN'] = x_auth_token

    recipe_id = st.text_input("Recipe ID")
    document_id = st.text_input("Document ID")

    if st.button("Get the Document"):
        if document_id and recipe_id and API_HOST and x_auth_token:
            display_document_object(recipe_id, document_id)
        else:
            st.warning("Please fill in the required fields to retrieve the document.")
    st.markdown("---")
    st.markdown("Copyright © 2023 Cognaize Engeneering LLC")


def display_document_object(recipe_id, document_id):
    st.title("Document Analysis Results")
    doc_object = Document.fetch_document(recipe_id, document_id)
    if not doc_object.is_xbrl:
        # Table analysis
        st.subheader("Table Analysis")
        try:
            extractor = table_analysis.TableAnalyzer(table_py_name="tables__table", threshold=0.5)
            fields_outside_of_tables = extractor.check_fields(doc_object)
            results_ = extractor.get_table_results()
            st.write("Mean and Standard Deviation of Tables:")
            if results_.empty:
                st.error('There are no tagged tables in this documents')
            else:
                st.dataframe(results_)
            st.write("Fields Outside of Tables:")
            if fields_outside_of_tables.empty:
                st.error('There are no fields tagged outside of tables')
            else:
                st.write(fields_outside_of_tables)

        except KeyError:
            st.error("The provided document object has no tables under the key")
    else:
        st.error("Document is in XBRL format, which is not supported for this analysis.")


if __name__ == "__main__":
    main()
