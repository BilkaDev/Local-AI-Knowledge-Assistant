import os
from datetime import datetime

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Local AI Knowledge Assistant", page_icon=":robot_face:")
    st.title("Local AI Knowledge Assistant")
    st.caption("Docker-first Day 2 smoke test")

    st.success("Streamlit app is running in Docker.")

    st.subheader("Environment check")
    st.write(f"APP_ENV: `{os.getenv('APP_ENV', 'not-set')}`")
    st.write(f"LLM_MODEL: `{os.getenv('LLM_MODEL', 'not-set')}`")
    st.write(f"OLLAMA_BASE_URL: `{os.getenv('OLLAMA_BASE_URL', 'not-set')}`")
    st.write(f"Timestamp: `{datetime.utcnow().isoformat()}Z`")

    st.subheader("Next step")
    st.info("Day 3 can now implement ingestion from `data/` and chunking.")


if __name__ == "__main__":
    main()
