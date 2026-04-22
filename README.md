# Vensim AI Local Web App

Энэ хувилбар нь локал дээр **dashboard + chatbot**-той ажиллана.

## Та хийх ганц зүйл
1. `.env` файлд `OPENAI_API_KEY=` дээр өөрийн API key-г оруулна.
2. `run.bat` файлыг ажиллуулна.
3. Browser дээр `http://127.0.0.1:8000` нээгдэнэ.

## Юу ажиллах вэ
- Dashboard дээр параметрийн утгыг өөрчлөхөд simulation шинэчлэгдэнэ.
- Chatbot нь model-aware асуулт, simulation асуулт, methodology асуулт, real-world асуултад хариулна.
- Model: `models/Daguul hot.mdl`

## Файлын бүтэц
- `web/` → HTML/CSS/JS frontend
- `app/` → Python backend + AI engine
- `models/` → `.mdl` model
- `output/` → Excel, PNG үр дүн

## Гол run файлууд
- `run.bat` → Local web app
- `run_cli.bat` → CLI
- `run_streamlit.bat` → Streamlit UI

## Package
Бүх шаардлагатай package `requirements.txt` дотор орсон.

## Анхаарах зүйл
- Dashboard дээрх `Симуляци эхлэх он` нь UI интервенц эхлэх хугацааг харуулах зориулалттай. Model дотроо time-based intervention байхгүй тул backend нь суурь ба scenario series-ийг тухайн оноос splice хийж харуулна.
- Chatbot-ын real-world answer mode нь OpenAI web search ашиглана.
