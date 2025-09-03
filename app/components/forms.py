import streamlit as st

def profile_form_from_schema(schema: dict, initial: dict | None = None, show_location=True):
    """
    Gera um formulário de perfil a partir do schema (igual ao usado nas páginas).
    Retorna (profile_dict, submitted: bool)
    """
    profile = dict(initial or {})
    with st.form("perfil_form_from_schema"):
        if show_location:
            c1, c2 = st.columns(2)
            with c1:
                profile["estado"] = st.text_input("Estado (UF)", value=profile.get("estado",""))
            with c2:
                profile["municipio"] = st.text_input("Município", value=profile.get("municipio",""))

        for field, spec in schema.items():
            if show_location and field in ("estado","municipio"):
                continue
            label = spec.get("label", field)
            t = spec.get("type", "text")
            prev = profile.get(field, "")
            if t == "text":
                profile[field] = st.text_input(label, value=str(prev))
            elif t == "number":
                profile[field] = st.number_input(label, value=float(prev or 0))
            elif t == "bool":
                profile[field] = st.checkbox(label, value=bool(prev))
            elif t == "select":
                options = spec.get("options", [])
                default = prev if prev in options else (options[0] if options else "")
                profile[field] = st.selectbox(label, options=options,
                                              index=options.index(default) if default in options else 0)
            else:
                profile[field] = st.text_input(label, value=str(prev))
        submitted = st.form_submit_button("Salvar alterações", type="primary")
    return profile, submitted