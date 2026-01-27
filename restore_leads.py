
import os

# 1. Leads from User Message (Text Paste)
text_leads = [
    "Татьяна None (@No Username) - ID: 1391226702",
    "Natia Kariauli (@No Username) - ID: 7738418497",
    "Анастасия Богословская (@fyalki) - ID: 999277747",
    "Ольга Ольга (@Olga2606Olga) - ID: 1365935250",
    "Яна None (@yana_merkulova13) - ID: 359989153",
    "Оксана Олейник | Маркетолог (@OksanaOlejnik) - ID: 1167312034",
    "🩷Ирина (Дет.спец.)🩷 None (@irinaGadel_777) - ID: 342731231",
    "Kati Yhh (@No Username) - ID: 585179105",
    "Наталья Камерзан (@nataliia_kamerzan) - ID: 461918190",
    "Евгения Белашова (@e_belashova) - ID: 132705784",
    "Anna Garmash (@anna_garmash) - ID: 322687974",
    "Tanya None (@that_girl_tata) - ID: 606557022",
    "Нелли None (@art_by_kulakova) - ID: 348160573",
    "Alina Brueckmann None (@alina_brueckmann) - ID: 696157468",
    "Di💠 None (@Di_Ala) - ID: 259622921",
    "Olya None (@Olya_B) - ID: 427434106",
    "Анна Ревва (@barmasweet) - ID: 197283839",
    "Svetlana Borodulina (@SvetlanaB37) - ID: 827946563",
    "Diana Gertsin (@dianagerts) - ID: 635045817",
    "Татьяна None (@tatiana_astroved) - ID: 1321564173",
]

# 2. Leads from Screenshot (Transcribed)
screenshot_leads = [
    "Гузель None (@guzelCreat) - ID: 258167458",
    "UPS911 None (@UPS911) - ID: 307997991",
    "Ольга Моталова (@zlukaM88) - ID: 205819038",
    "Евгения Белашова (@e_belashova) - ID: 132705784",
    "Anna designer (@Anna_disigner) - ID: 1461645462",
    "Светлана None (@SV0675) - ID: 1686161167",
    "Кристина None (@Kristina_Govorova) - ID: 455128786",
    "Elena None (@E_ilkaeva) - ID: 438917783",
    "Алена None (@No Username) - ID: 907358063",
    "Анастасия Гарбуз (@No Username) - ID: 1134920390",
    "Светлана None (@SvetaIlyasova) - ID: 434535050",
    "Oxana None (@OxanaLuz) - ID: 1899655498",
    "Alena Alena (@No Username) - ID: 6007830286",
    "Раиса None (@No Username) - ID: 363814965",
    "Vmv None (@No Username) - ID: 226490373",
    "Анна ИваNOVA None (@Ivanova_Any_g) - ID: 651030161",
    "Elena Tkach (@lenaelenatkach) - ID: 313784952",
    "Дарья Буркут (@darya_burkut_project) - ID: 725817685",
    "Ардаза None (@ardashazhan) - ID: 630654200",
    "Daria None (@daria_nekrasovas) - ID: 957755530",
    "Roman Chystiakov (@chistyakovroman) - ID: 472199234",
    "Ксения None (@Doomeralia) - ID: 47638674",
    "Çekiç Zarina (@No Username) - ID: 1596764666",
    "Ольга None (@Evhelga) - ID: 464385960",
    "Tatiana TM (@Ta21ana) - ID: 53965736",
    "Лола А (@LolaAcosmit) - ID: 1082406302",
    "Ольга Петрова (@olgapetrova_stylist) - ID: 240995745",
    "Лариса Егорова 🦢 (@larisa_v_egorova) - ID: 500942259",
    "M P (@No Username) - ID: 931049927",
    "Ширин Рыскулбекова (@Shirin_Ryskulbekova) - ID: 757720551",
    "Elena Barasova (@Jelena_Barasova) - ID: 492975354",
    "Марина Кулик (@marina_kulik8) - ID: 522187697",
    "Dilara Gavrilenko(Khafizova) (@No Username) - ID: 1033153865",
    "Адинай None (@adinai_naksat) - ID: 5415413917",
    "Кристина Яценко (@Yatsenko_kriss) - ID: 386739565",
    "Anastasia None (@annyita) - ID: 614231100",
    "Elfia None (@elfia_interior) - ID: 1159685649",
    "Nina None (@ninasushko) - ID: 230270812",
    "Alv None (@No Username) - ID: 5147743447",
    "Di💠 None (@Di_Ala) - ID: 259622921",
    "Ольга Лукашевич (@No Username) - ID: 1384979877",
    "Katrin None (@Katrin_1271) - ID: 1544769341",
    "Ольга None (@OlgaAnatolievnaN) - ID: 452768646",
    "Mary Kap None (@maxkaidi) - ID: 257718247",
    "Diana None (@DK_nknsk) - ID: 1207741702",
    "Алина None (@No Username) - ID: 978173316",
    "Фотограф Лена Терещенко (@tereshchenko_photo) - ID: 901981196",
    "@tane4ka7777 None (@No Username) - ID: 1025851566",
    "Lena Maier (@No Username) - ID: 1166547268",
    "Lucy Rosenthal (@lu_rosen) - ID: 1069040845",
    "Надежда Епаева (@dul091) - ID: 947228728"
]

# 3. Leads from Original File (User Paste)
original_leads = [
    "Anna Romeo ВАСТУ-дизайнер интерьеров INTERIOR DESIGN (@annaromeodesign) - ID: 842443917",
    "Тимур None (@tymuron) - ID: 1873528397",
    "Ксения | ИНТЕРЬЕРНЫЕ КАРТИНЫ Картины в премиальных техниках (@kseniya_oprio) - ID: 162903116",
    "Екатерина None (@Churakova_Kat) - ID: 514549494",
    "Малика Саматовна (@dr_samatovna) - ID: 738779679",
    "Ok@sana None (No Username) - ID: 687854628",
    "Kati Yhh (No Username) - ID: 585179105",
    "Анастасия None (@anastasiya_berid) - ID: 1301033384",
    "Anastasiya None (@ananas7ananas7) - ID: 7018828404",
    "Julia Mironova (@Julia_A_Mironova) - ID: 961505234",
    "Ирина Андриянова (@irina_andriyanova) - ID: 6572981296",
    "Елена Мартин (@Sstaffa) - ID: 852199702",
    "Аnastasia None (No Username) - ID: 909425661",
    "Alena Akinshina None (@alena_active) - ID: 628777218",
    "Anastasiya None (No Username) - ID: 247755772",
    "Олеся| Аюрведа (@olesya_dietolog) - ID: 240096163",
    "Юля None (@Ulixanna) - ID: 992387202",
    "Марго Духовная (@Margo_Dukhovnaya) - ID: 309059080",
    "Оксана Олейник | Маркетолог (@OksanaOlejnik) - ID: 1167312034",
    "Марина Кулик (@marina_kulik8) - ID: 522187697",
    "Ольга Власенко (No Username) - ID: 1083520202",
    "Юлия Ванькова Api (@Uv_API) - ID: 5131454149",
    "🩵 Ирина Юрьевна 🩵 None (@solnze_nino) - ID: 773945497"
]

all_raw = text_leads + screenshot_leads + original_leads
unique_leads = {}

for line in all_raw:
    try:
        # Extract ID
        parts = line.split("ID: ")
        if len(parts) > 1:
            chat_id = parts[1].strip()
            # Use ID as key to deduplicate
            unique_leads[chat_id] = line.strip()
    except Exception as e:
        print(f"Error parsing line: {line} - {e}")

# Write to file
with open("waitlist.txt", "w") as f:
    for line in unique_leads.values():
        f.write(line + "\n")

print(f"Successfully restored {len(unique_leads)} unique leads to waitlist.txt")
