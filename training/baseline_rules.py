"""Reglas y palabras usadas por el baseline de expresiones regulares."""

PATRONES_OFERTA = [
    r"\bestamos buscando\b",
    r"\bbuscamos (a )?(un|una)\b",
    r"\bse busca\b",
    r"\bwe(’|'| )?re hiring\b",
    r"\bwe are hiring\b",
    r"\bhiring a\b",
    r"\bis hiring\b",
    r"\bjoin our team\b",
    r"\bunete a nuestro equipo\b",
    r"\babrimos vacante\b",
    r"\bnueva vacante\b",
    r"\bvacante disponible\b",
    r"\bvacante para\b",
    r"\benvia tu cv a\b",
    r"\benvianos tu cv\b",
    r"\bpostulate\b",
    r"\bpostula aqui\b",
    r"\bapply now\b",
    r"\bapply here\b",
    r"\bfor our client\b",
    r"\bpara nuestro cliente\b",
    r"\blooking for (a|an) [a-z\s]{0,25}"
    r"(developer|engineer|designer|programador|desarrollador)\b",
    r"\b(we|our (team|company|client)) " r"(are |is )?(hiring|looking for)\b",
]

PATRONES_CANDIDATO = [
    r"#?opentowork",
    r"\bopen to work\b",
    r"\bestoy buscando (trabajo|empleo|oportunidad)\b",
    r"\bbusco (trabajo|empleo|nueva oportunidad|oportunidad laboral)\b",
    r"\bdisponible para nuevas oportunidades\b",
    r"\ben busqueda activa de trabajo\b",
    r"\bmi (cv|hoja de vida|portafolio)\b",
    r"\bcontactame\b",
    r"\bdm me\b",
    r"\bescribeme (al|a)\b",
    r"\brecien (egresado|graduado)\b",
    r"\b(i'?m|im|estoy) (actively )?"
    r"(looking for|buscando) (a |an |una |un )?(new )?"
    r"(opportunity|role|position|job|oportunidad|trabajo|empleo)\b",
]

PATRONES_RUIDO_SOCIAL = [
    r"\bfeliz cumpleanos\b",
    r"\bhappy birthday\b",
    r"\baniversario laboral\b",
    r"\bwork anniversary\b",
    r"\bestoy feliz de anunciar\b",
    r"\bexcited to announce\b",
    r"\bme uno a\b",
    r"\b(i'?m|im) joining\b",
    r"\bfelicidades a\b",
    r"\bcongratulations to\b",
    r"\borgulloso de compartir\b",
    r"\bproud to share\b",
    r"\bnuevo puesto en\b",
    r"\bnuevo cargo en\b",
    r"\bcelebrando\b",
    r"\bcelebrating\b",
]

SENALES_CONTRATACION = [
    "estamos buscando",
    "buscamos",
    "hiring",
    "we are hiring",
    "we're hiring",
    "vacante",
    "open position",
    "busqueda activa",
    "oportunidad laboral",
    "looking for a",
    "se busca",
    "join our team",
    "nueva busqueda",
]

SENALES_APLICACION = [
    "envia tu cv",
    "envianos tu cv",
    "postula",
    "aplica",
    "apply",
    "comparte tu cv",
    "send your resume",
    "send your cv",
    "hoja de vida",
    "link en comentarios",
    "dm me",
    "escribeme",
]

CORE = {
    "react": 3,
    "next.js": 3,
    "nextjs": 3,
    "typescript": 3,
    "frontend": 3,
    "front-end": 3,
    "front end": 3,
    "vtex": 3,
}

SECUNDARIO = {
    "javascript": 1,
    "node": 1,
    "graphql": 1,
    "tailwind": 1,
    "e-commerce": 1,
    "ecommerce": 1,
    "remoto": 1,
    "remote": 1,
    "latam": 1,
    "jest": 1,
    "redux": 1,
    "seo": 1,
    "lighthouse": 1,
}

VETO = [
    "nestjs",
    "nest.js",
    "kubernetes",
    "kafka",
    "rabbitmq",
    "terraform",
    "php",
    "laravel",
    ".net",
    "dotnet",
    "react native",
    "flutter",
    "angular",
    "java developer",
    "spring boot",
    "python developer",
    "golang",
    "ingles avanzado",
    "advanced english",
    "fluent english",
    "english c1",
    "excellent english",
    "ingles fluido",
]

UMBRAL_REVISAR = 4
UMBRAL_TALVEZ = 1
