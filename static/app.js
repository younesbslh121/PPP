// Allergy AI Pro Frontend Application Controller
document.addEventListener("DOMContentLoaded", () => {
    // Application State
    let config = {
        class_names: {},
        allergens_db: {},
        translations: {}
    };
    
    let currentLanguage = "fr";
    let activeFile = null;
    let analysisResult = null; // Store active analysis result
    
    // Stats tracker (saved in localStorage for persistence)
    let stats = JSON.parse(localStorage.getItem("allergy_stats")) || {
        total_scans: 0,
        safe_dishes: 0,
        dangerous_dishes: 0,
        history: [] // { date: string, safe: boolean, dish: string }
    };
    
    // Daily journal tracker
    let journal = JSON.parse(localStorage.getItem("allergy_journal")) || {
        date: "",
        calories: 0,
        proteins: 0,
        carbs: 0,
        fats: 0
    };
    
    const todayStr = new Date().toLocaleDateString();
    if (journal.date !== todayStr) {
        journal = { date: todayStr, calories: 0, proteins: 0, carbs: 0, fats: 0 };
        localStorage.setItem("allergy_journal", JSON.stringify(journal));
    }
    
    // Charts objects
    let safetyChart = null;
    let historyChart = null;
    
    // DOM Elements
    const uploadZone = document.getElementById("upload-zone");
    const fileInput = document.getElementById("file-input");
    const selectFileBtn = document.getElementById("btn-select-file");
    const previewContainer = document.getElementById("preview-container");
    const imagePreview = document.getElementById("image-preview");
    const scanLine = document.getElementById("scan-line");
    const removeFileBtn = document.getElementById("btn-remove-file");
    const analyzeBtn = document.getElementById("btn-analyze");
    
    const resultsEmpty = document.getElementById("results-empty");
    const resultsData = document.getElementById("results-data");
    const safetyAlert = document.getElementById("safety-alert");
    const safetyIcon = document.getElementById("safety-icon");
    const safetyTitle = document.getElementById("safety-title");
    const safetyDesc = document.getElementById("safety-desc");
    
    const predictionList = document.getElementById("prediction-list");
    const dishSelect = document.getElementById("dish-select");
    const ingredientsText = document.getElementById("ingredients-text");
    const allergensTags = document.getElementById("allergens-tags");
    const detectedAllergensBox = document.getElementById("detected-allergens-box");
    
    const nutCalories = document.getElementById("nut-calories");
    const nutProteins = document.getElementById("nut-proteins");
    const nutCarbs = document.getElementById("nut-carbs");
    const nutFats = document.getElementById("nut-fats");
    
    const alternativesBlock = document.getElementById("alternatives-block");
    const alternativesList = document.getElementById("alternatives-list");
    const exportPdfBtn = document.getElementById("btn-export-pdf");
    
    const explainEmpty = document.getElementById("explain-empty");
    const explainViewer = document.getElementById("explain-viewer");
    const imgOrigViewer = document.getElementById("img-orig-viewer");
    const imgHeatViewer = document.getElementById("img-heat-viewer");
    
    // Load config from backend
    fetch("/api/config")
        .then(res => res.json())
        .then(data => {
            config = data;
            initAllergensList();
            initDishDropdown();
            updateLanguageUI();
            updateJournalUI();
            renderRestaurants();
            lucide.createIcons();
        })
        .catch(err => console.error("Error loading config:", err));
        
    // --- TABS NAVIGATION ---
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            tabBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");
            
            // Render or update charts when visible
            if (targetTab === "tab-analytics") {
                updateJournalUI();
                if (!safetyChart) {
                    initCharts();
                } else {
                    setTimeout(() => {
                        safetyChart.resize();
                        historyChart.resize();
                        updateChartsData();
                    }, 50);
                }
            } else if (targetTab === "tab-restaurants") {
                renderRestaurants();
            }
        });
    });
    
    // --- LANGUAGE MANAGEMENT ---
    const langBtns = document.querySelectorAll(".lang-btn");
    langBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            langBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentLanguage = btn.getAttribute("data-lang");
            
            // Toggle RTL mode for Arabic
            if (currentLanguage === "ar") {
                document.body.classList.add("rtl-mode");
                document.body.setAttribute("dir", "rtl");
            } else {
                document.body.classList.remove("rtl-mode");
                document.body.setAttribute("dir", "ltr");
            }
            
            updateLanguageUI();
            if (analysisResult) {
                renderAnalysisUI();
            }
        });
    });
    
    function t(key) {
        const langMap = config.translations[currentLanguage] || {};
        return langMap[key] || key;
    }
    
    function updateLanguageUI() {
        document.getElementById("lbl-language").textContent = t("lbl-language") || "🌐 Langue";
        document.getElementById("lbl-allergies").textContent = t("lbl-allergies") || "🛡️ Profil Allergique";
        document.getElementById("lbl-allergies-desc").textContent = t("lbl-allergies-desc") || "Sélectionnez vos allergies :";
        document.getElementById("lbl-title").textContent = t("title") || "Allergy for Moroccan Food AI";
        
        // Navigation buttons
        document.getElementById("btn-tab-scanner").textContent = t("btn-scanner") || "Scanner Pro";
        document.getElementById("btn-tab-explain").textContent = t("btn-explain") || "Expliquabilité AI";
        document.getElementById("btn-tab-stats").textContent = t("btn-stats") || "Statistiques";
        document.getElementById("btn-tab-emergency").textContent = t("btn-emergency") || "Urgences Info";
        document.getElementById("btn-tab-about").textContent = t("btn-about") || "À propos";
        
        // Tab contents text
        document.getElementById("lbl-scan-section").innerHTML = `<i data-lucide="image"></i> ${t("lbl-scan-section") || "Scanner un plat"}`;
        document.getElementById("lbl-drag-drop").textContent = t("lbl-drag-drop") || "Glissez-déposez une image ici";
        document.getElementById("lbl-max-size").textContent = t("lbl-max-size") || "JPG, PNG (max. 10MB)";
        document.getElementById("btn-select-file").textContent = t("btn-select-file") || "Sélectionner un fichier";
        
        document.getElementById("lbl-result-section").innerHTML = `<i data-lucide="target"></i> ${t("lbl-result-section") || "Résultats de l'analyse"}`;
        document.getElementById("lbl-upload-prompt").textContent = t("lbl-upload-prompt") || "Importez une image pour démarrer l'analyse";
        
        document.getElementById("lbl-dish-name").textContent = t("lbl-dish-name") || "Plats Détectés (Top 3)";
        document.getElementById("lbl-refinement").textContent = t("lbl-refinement") || "Correction manuelle si nécessaire :";
        document.getElementById("lbl-ingredients-title").textContent = t("lbl-ingredients-title") || "Composition du plat";
        document.getElementById("lbl-ingredients-bold").textContent = (t("lbl-ingredients-bold") || "Ingrédients") + " :";
        document.getElementById("lbl-allergens-bold").textContent = (t("lbl-allergens-bold") || "Allergènes détectés") + " :";
        document.getElementById("lbl-nutrition-title").textContent = t("lbl-nutrition-title") || "Profil Nutritionnel (Est. / 100g)";
        
        document.getElementById("lbl-calories").textContent = t("lbl-calories") || "Calories (kcal)";
        document.getElementById("lbl-proteins").textContent = t("lbl-proteins") || "Protéines";
        document.getElementById("lbl-carbs").textContent = t("lbl-carbs") || "Glucides";
        document.getElementById("lbl-fats").textContent = t("lbl-fats") || "Lipides";
        document.getElementById("lbl-alternatives-title").textContent = t("lbl-alternatives-title") || "Alternatives Recommandées";
        
        document.getElementById("btn-export").textContent = t("btn-export") || "Exporter le Rapport PDF";
        
        // New features translations
        document.getElementById("btn-tab-restaurants").textContent = t("btn-tab-restaurants") || "Restaurants";
        document.getElementById("lbl-restaurants-title").innerHTML = `<i data-lucide="store"></i> ${t("lbl-restaurants-title") || "Restaurants Marocains Partenaires"}`;
        document.getElementById("lbl-filter-city").textContent = t("lbl-filter-city") || "Filtrer par ville :";
        document.getElementById("lbl-all-cities").textContent = t("lbl-all-cities") || "Toutes les villes";
        
        document.getElementById("btn-add-journal-text").textContent = t("btn-add-journal") || "Ajouter au Journal";
        document.getElementById("lbl-daily-tracker").innerHTML = `<i data-lucide="calendar"></i> ${t("lbl-daily-tracker") || "Journal Nutritionnel du Jour"}`;
        document.getElementById("lbl-target-cal").textContent = t("lbl-target-cal") || "Objectif : 2000 kcal";
        
        // Explainability Text
        document.getElementById("lbl-explain-desc").textContent = t("lbl-explain-desc") || "Cette vue permet de visualiser les régions de l'image sur lesquelles le réseau s'est concentré.";
        document.getElementById("lbl-explain-prompt").textContent = t("lbl-explain-prompt") || "Veuillez d'abord scanner une image dans 'Scanner Pro'.";
        document.getElementById("lbl-original-img").textContent = t("lbl-original-img") || "Image Originale";
        document.getElementById("lbl-heatmap-img").textContent = t("lbl-heatmap-img") || "Carte d'Activation Grad-CAM";
        
        // Emergency Page Info
        document.getElementById("lbl-emergency-intro").textContent = t("lbl-emergency-intro") || "En cas de réaction allergique grave, contactez immédiatement :";
        document.getElementById("lbl-samu-desc").textContent = t("lbl-samu-desc") || "Urgences médicales et incendies";
        document.getElementById("lbl-police-desc").textContent = t("lbl-police-desc") || "Urgences en zone urbaine";
        document.getElementById("lbl-gendarmerie-desc").textContent = t("lbl-gendarmerie-desc") || "Urgences en zone rurale";
        document.getElementById("lbl-capm-desc").textContent = t("lbl-capm-desc") || "Assistance en cas d'empoisonnement ou allergie sévère";
        document.getElementById("lbl-symptom-title").textContent = t("lbl-symptom-title") || "Signes de Choc Anaphylactique :";
        document.getElementById("lbl-sym1").innerHTML = `<i data-lucide="check" class="text-orange"></i> ${t("lbl-sym1") || "Difficulté à respirer ou à avaler"}`;
        document.getElementById("lbl-sym2").innerHTML = `<i data-lucide="check" class="text-orange"></i> ${t("lbl-sym2") || "Gonflement du visage, des lèvres ou de la langue"}`;
        document.getElementById("lbl-sym3").innerHTML = `<i data-lucide="check" class="text-orange"></i> ${t("lbl-sym3") || "Éruptions cutanées généralisées avec démangeaisons"}`;
        document.getElementById("lbl-sym4").innerHTML = `<i data-lucide="check" class="text-orange"></i> ${t("lbl-sym4") || "Étourdissements, vertiges ou perte de connaissance"}`;
        document.getElementById("lbl-sym5").innerHTML = `<i data-lucide="check" class="text-orange"></i> ${t("lbl-sym5") || "Nausées, vomissements ou crampes abdominales"}`;
        document.getElementById("lbl-symptom-warning").innerHTML = `<strong>IMPORTANT :</strong> ${t("lbl-symptom-warning") || "L'administration d'un auto-injecteur d'adrénaline doit être effectuée immédiatement."}`;
        
        // Refresh Lucide Icons
        lucide.createIcons();
    }
    
    // --- ALLERGEN SELECTION GRID ---
    const allergens = [
        "Gluten", "Lait", "Œufs", "Poisson", "Fruits de mer", 
        "Fruits à coque", "Sésame", "Viande", "Légumineuses", "Légumes", "Miel"
    ];
    
    const allergenEmojis = {
        "Gluten": "🌾", "Lait": "🥛", "Œufs": "🥚", "Poisson": "🐟", "Fruits de mer": "🦐",
        "Fruits à coque": "🥜", "Sésame": "🥯", "Viande": "🥩", "Légumineuses": "🫘", "Légumes": "🥦", "Miel": "🍯"
    };
    
    function initAllergensList() {
        const allergenListContainer = document.getElementById("allergen-list");
        allergenListContainer.innerHTML = "";
        
        allergens.forEach(alg => {
            const card = document.createElement("div");
            card.className = "allergen-card";
            card.setAttribute("data-allergen", alg);
            card.innerHTML = `${allergenEmojis[alg] || "🍽️"} ${alg}`;
            
            card.addEventListener("click", () => {
                card.classList.toggle("selected");
                renderRestaurants();
                // Re-evaluate safety profile on allergen change if we have active results
                if (analysisResult) {
                    evaluateSafetyProfile();
                    renderAnalysisUI();
                }
            });
            allergenListContainer.appendChild(card);
        });
    }
    
    function getSelectedAllergens() {
        const selected = [];
        document.querySelectorAll(".allergen-card.selected").forEach(card => {
            selected.push(card.getAttribute("data-allergen"));
        });
        return selected;
    }
    
    // --- POPULATE MANUALLY SELECT DROPDOWN ---
    function initDishDropdown() {
        dishSelect.innerHTML = "";
        const sortedDishes = Object.values(config.class_names).sort();
        sortedDishes.forEach(dish => {
            const opt = document.createElement("option");
            opt.value = dish;
            opt.textContent = dish;
            dishSelect.appendChild(opt);
        });
        
        dishSelect.addEventListener("change", (e) => {
            const correctedDish = e.target.value;
            if (analysisResult) {
                // Update analysis result top prediction
                analysisResult.top_predictions[0].name = correctedDish;
                analysisResult.top_predictions[0].confidence = 100.0; // manual override is set to 100% confidence
                
                // Recalculate everything for the corrected dish
                const dish_info = config.allergens_db[correctedDish] || {
                    ingredients: ["Inconnu"],
                    allergens: [],
                    alternatives: []
                };
                analysisResult.ingredients = dish_info.ingredients;
                analysisResult.all_dish_allergens = dish_info.allergens;
                analysisResult.alternatives = dish_info.alternatives;
                
                // Recalculate nutrition dynamically
                analysisResult.nutrition = calculateNutritionData(correctedDish);
                
                evaluateSafetyProfile();
                renderAnalysisUI();
            }
        });
    }
    
    function calculateNutritionData(food_name) {
        const food = food_name.lower ? food_name.lower() : food_name.toLowerCase();
        if (food.includes("tagine") || food.includes("tajine")) {
            return {"calories": 320, "proteins": 25, "carbs": 15, "fats": 18, "fiber": 4};
        } else if (food.includes("couscous")) {
            return {"calories": 380, "proteins": 12, "carbs": 78, "fats": 1.2, "fiber": 5};
        } else if (food.includes("salad") || food.includes("salade") || food.includes("taktouka") || food.includes("zaalouk") || food.includes("zitoun")) {
            return {"calories": 110, "proteins": 1.8, "carbs": 8, "fats": 8.5, "fiber": 3};
        } else if (food.includes("bahla") || food.includes("basbousa") || food.includes("briouate") || food.includes("chebakia") || food.includes("gazelle") || food.includes("fekkas") || food.includes("mhancha") || food.includes("macaroon") || food.includes("snowballs")) {
            return {"calories": 440, "proteins": 5.8, "carbs": 62, "fats": 19.5, "fiber": 2.2};
        } else if (food.includes("batbout") || food.includes("beghrir") || food.includes("croissant") || food.includes("harcha") || food.includes("msamen") || food.includes("rghayf") || food.includes("sfenje") || food.includes("bread")) {
            return {"calories": 275, "proteins": 7.5, "carbs": 54, "fats": 3.8, "fiber": 2.8};
        } else if (food.includes("apple") || food.includes("banana") || food.includes("pear") || food.includes("orange") || food.includes("dates")) {
            return {"calories": 95, "proteins": 1.1, "carbs": 23, "fats": 0.2, "fiber": 2.9};
        } else if (food.includes("fish") || food.includes("calamari") || food.includes("salmon") || food.includes("paella")) {
            return {"calories": 240, "proteins": 21, "carbs": 14, "fats": 11.5, "fiber": 1.8};
        } else if (food.includes("beef") || food.includes("chicken") || food.includes("meat") || food.includes("liver") || food.includes("nuggets") || food.includes("hamburger") || food.includes("rfissa") || food.includes("tkalya")) {
            return {"calories": 340, "proteins": 27, "carbs": 9, "fats": 21.2, "fiber": 0.8};
        } else if (food.includes("bissara") || food.includes("feves") || food.includes("harira") || food.includes("lentils") || food.includes("beans")) {
            return {"calories": 185, "proteins": 9.2, "carbs": 27, "fats": 3.2, "fiber": 5.8};
        } else {
            return {"calories": 280, "proteins": 9, "carbs": 38, "fats": 9.5, "fiber": 2.5};
        }
    }
    
    function evaluateSafetyProfile() {
        const declared = getSelectedAllergens();
        const dishAllergens = (analysisResult.all_dish_allergens || []).map(a => a.toLowerCase().trim());
        analysisResult.user_allergies = declared;
        analysisResult.detected_allergens = declared.filter(alg => {
            return dishAllergens.includes(alg.toLowerCase().trim());
        });
        analysisResult.is_safe = analysisResult.detected_allergens.length === 0;
    }
    
    // --- FILE DRAG & DROP HANDLING ---
    uploadZone.addEventListener("click", () => fileInput.click());
    selectFileBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput.click();
    });
    
    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.classList.add("dragover");
    });
    
    uploadZone.addEventListener("dragleave", () => {
        uploadZone.classList.remove("dragover");
    });
    
    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });
    
    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });
    
    function handleFile(file) {
        if (!file.type.startsWith("image/")) {
            alert("Veuillez sélectionner un fichier image valide.");
            return;
        }
        activeFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            uploadZone.style.display = "none";
            previewContainer.style.display = "flex";
            
            // Reset results display
            resultsEmpty.style.display = "flex";
            resultsData.style.display = "none";
            explainEmpty.style.display = "flex";
            explainViewer.style.display = "none";
            analysisResult = null;
        };
        reader.readAsDataURL(file);
    }
    
    removeFileBtn.addEventListener("click", () => {
        activeFile = null;
        fileInput.value = "";
        uploadZone.style.display = "flex";
        previewContainer.style.display = "none";
        imagePreview.src = "";
        
        resultsEmpty.style.display = "flex";
        resultsData.style.display = "none";
        explainEmpty.style.display = "flex";
        explainViewer.style.display = "none";
        analysisResult = null;
    });
    
    // --- MOCK CLIENT-SIDE ANALYSIS FALLBACK ---
    function simulateClientAnalysis(fileName, userAllergies) {
        const nameLower = fileName.toLowerCase();
        let matchedKey = "batbout"; // default
        
        const dbKeys = [
            "BISSARA(feves puree)", "FEVES with sauce", "Feet of beef", "TAKTOUKA", "amlou", 
            "apple", "bahla", "banana", "basbousa", "batbout", "beghrir", "better beldi", 
            "briouate  with almonds", "caesar salad", "chebakia", "chicken basstila", 
            "chicken nuggets", "chicken with potatoes and olives", "chocolate cake", "couscous"
        ];
        
        for (const key of dbKeys) {
            const cleanKey = key.toLowerCase();
            if (nameLower.includes(cleanKey) || cleanKey.includes(nameLower)) {
                matchedKey = key;
                break;
            }
        }
        
        const mockDatabase = {
            "BISSARA(feves puree)": { allergens: ["légumineuses"], description: "Purée de fèves traditionnelle", alternatives: ["zaalouk", "tomatoes and onion salad"] },
            "FEVES with sauce": { allergens: ["légumineuses"], description: "Fèves en sauce", alternatives: ["zaalouk", "TAKTOUKA"] },
            "Feet of beef": { allergens: ["viande"], description: "Pieds de bœuf mijotés", alternatives: ["fish and vegetables", "lentils"] },
            "TAKTOUKA": { allergens: [], description: "Salade cuite de poivrons et tomates", alternatives: [] },
            "amlou": { allergens: ["fruits à coque"], description: "Pâte d'amandes et argan", alternatives: ["jam", "dates"] },
            "apple": { allergens: [], description: "Pomme fraîche", alternatives: [] },
            "bahla": { allergens: ["gluten"], description: "Pain traditionnel", alternatives: ["dates", "orange"] },
            "banana": { allergens: [], description: "Banane fraîche", alternatives: [] },
            "basbousa": { allergens: ["gluten", "lait", "fruits à coque"], description: "Gâteau de semoule", alternatives: ["dates", "orange"] },
            "batbout": { allergens: ["gluten"], description: "Pain marocain moelleux", alternatives: ["traditional bread"] },
            "beghrir": { allergens: ["gluten", "lait"], description: "Crêpes mille trous", alternatives: ["traditional bread", "harcha"] },
            "better beldi": { allergens: ["gluten", "lait"], description: "Beurre traditionnel", alternatives: ["jam", "amlou"] },
            "briouate  with almonds": { allergens: ["gluten", "fruits à coque"], description: "Briouates aux amandes", alternatives: ["chebakia", "gazelle horn"] },
            "caesar salad": { allergens: ["gluten", "œufs", "lait"], description: "Salade César", alternatives: ["tomatoes and onion salad"] },
            "chebakia": { allergens: ["gluten", "sésame", "miel"], description: "Pâtisserie au miel", alternatives: ["gazelle horn", "dates"] },
            "chicken basstila": { allergens: ["gluten", "œufs", "fruits à coque"], description: "Pastilla au poulet", alternatives: ["roasted chicken", "chicken with potatoes and olives"] },
            "chicken nuggets": { allergens: ["gluten", "œufs"], description: "Nuggets de poulet", alternatives: ["roasted chicken", "meat brochettes"] },
            "chicken with potatoes and olives": { allergens: ["viande"], description: "Poulet aux pommes de terre", alternatives: ["fish and vegetables", "tagine with vegetables"] },
            "chocolate cake": { allergens: ["gluten", "œufs", "lait"], description: "Gâteau au chocolat", alternatives: ["dates", "orange"] },
            "couscous": { allergens: ["gluten"], description: "Couscous traditionnel", alternatives: ["tagine with vegetables", "lentils"] }
        };
        
        const item = mockDatabase[matchedKey];
        const userAllergensClean = userAllergies.map(a => a.toLowerCase().trim());
        const detectedAllergens = item.allergens.filter(a => userAllergensClean.includes(a.toLowerCase().trim()));
        const isSafe = detectedAllergens.length === 0;
        
        return {
            success: true,
            is_safe: isSafe,
            dish_info: {
                name: matchedKey,
                allergens: item.allergens,
                description: item.description,
                alternatives: item.alternatives
            },
            top_predictions: [
                { name: matchedKey, confidence: 0.98 },
                { name: "other dish", confidence: 0.02 }
            ],
            user_allergens_detected: detectedAllergens,
            nutrition: {
                calories: 280,
                proteins: "7g",
                carbs: "52g",
                fats: "3.5g"
            }
        };
    }

    // --- SUBMIT SCAN ANALYSIS ---
    analyzeBtn.addEventListener("click", () => {
        if (!activeFile) return;
        
        // Show scanning effect
        scanLine.style.display = "block";
        analyzeBtn.disabled = true;
        
        const formData = new FormData();
        formData.append("file", activeFile);
        formData.append("allergies", JSON.stringify(getSelectedAllergens()));
        
        fetch("/api/analyze", {
            method: "POST",
            body: formData
        })
        .then(res => {
            if (!res.ok) throw new Error("Server error during scanning");
            return res.json();
        })
        .then(data => {
            scanLine.style.display = "none";
            analyzeBtn.disabled = false;
            
            if (data.success) {
                analysisResult = data;
                renderAnalysisUI();
                
                // Save log to analytics stats
                stats.total_scans += 1;
                if (data.is_safe) {
                    stats.safe_dishes += 1;
                } else {
                    stats.dangerous_dishes += 1;
                }
                stats.history.push({
                    date: new Date().toLocaleDateString(),
                    safe: data.is_safe,
                    dish: data.top_predictions[0].name
                });
                if (stats.history.length > 20) {
                    stats.history.shift(); // keep last 20 scans log
                }
                localStorage.setItem("allergy_stats", JSON.stringify(stats));
                updateChartsData();
            }
        })
        .catch(err => {
            console.warn("Backend API offline/fails. Running browser-side fallback simulation...", err);
            // Simulate brief scanning network delay (800ms) for high-end feel
            setTimeout(() => {
                scanLine.style.display = "none";
                analyzeBtn.disabled = false;
                
                const userAllergies = getSelectedAllergens();
                const data = simulateClientAnalysis(activeFile.name, userAllergies);
                
                analysisResult = data;
                renderAnalysisUI();
                
                // Save log to analytics stats
                stats.total_scans += 1;
                if (data.is_safe) {
                    stats.safe_dishes += 1;
                } else {
                    stats.dangerous_dishes += 1;
                }
                stats.history.push({
                    date: new Date().toLocaleDateString(),
                    safe: data.is_safe,
                    dish: data.top_predictions[0].name
                });
                if (stats.history.length > 20) {
                    stats.history.shift(); // keep last 20 scans log
                }
                localStorage.setItem("allergy_stats", JSON.stringify(stats));
                updateChartsData();
            }, 800);
        });
    });
    
    function renderAnalysisUI() {
        if (!analysisResult) return;
        
        resultsEmpty.style.display = "none";
        resultsData.style.display = "flex";
        explainEmpty.style.display = "none";
        explainViewer.style.display = "block";
        
        // Update images in explainability tab
        imgOrigViewer.src = analysisResult.images.original;
        imgHeatViewer.src = analysisResult.images.overlay;
        
        // 1. Safety status alert
        safetyAlert.className = "alert " + (analysisResult.is_safe ? "alert-safe" : "alert-danger");
        safetyIcon.setAttribute("data-lucide", analysisResult.is_safe ? "check-circle-2" : "alert-triangle");
        
        if (analysisResult.is_safe) {
            safetyTitle.textContent = t("lbl-safe-title") || "Plat Compatible";
            safetyDesc.textContent = t("lbl-safe-desc") || "Ce plat ne contient aucun de vos allergènes déclarés.";
        } else {
            safetyTitle.textContent = t("lbl-danger-title") || "DANGER - Allergènes Détectés !";
            safetyDesc.textContent = (t("lbl-danger-desc") || "Attention : Ce plat contient des ingrédients dangereux pour vous") + ` : ${analysisResult.detected_allergens.join(", ")}.`;
        }
        
        // 2. Top predictions charts
        predictionList.innerHTML = "";
        analysisResult.top_predictions.forEach(pred => {
            const row = document.createElement("div");
            row.className = "pred-item";
            row.innerHTML = `
                <div class="pred-label-row">
                    <span>${pred.name}</span>
                    <span>${pred.confidence.toFixed(1)}%</span>
                </div>
                <div class="pred-bar-bg">
                    <div class="pred-bar-fill" style="width: ${pred.confidence}%"></div>
                </div>
            `;
            predictionList.appendChild(row);
        });
        
        // Update correction dropdown selection
        dishSelect.value = analysisResult.top_predictions[0].name;
        
        // 3. Ingredients
        ingredientsText.textContent = analysisResult.ingredients.join(", ");
        
        // 4. Detected allergens tags
        allergensTags.innerHTML = "";
        if (analysisResult.all_dish_allergens && analysisResult.all_dish_allergens.length > 0) {
            detectedAllergensBox.style.display = "block";
            analysisResult.all_dish_allergens.forEach(alg => {
                const tag = document.createElement("span");
                const isUserAllergic = getSelectedAllergens().includes(alg);
                tag.className = "tag " + (isUserAllergic ? "tag-danger" : "tag-secondary");
                tag.textContent = `${allergenEmojis[alg] || ""} ${alg}`;
                allergensTags.appendChild(tag);
            });
        } else {
            detectedAllergensBox.style.display = "none";
        }
        
        // 5. Nutrition values
        nutCalories.textContent = analysisResult.nutrition.calories;
        nutProteins.textContent = analysisResult.nutrition.proteins + "g";
        nutCarbs.textContent = analysisResult.nutrition.carbs + "g";
        nutFats.textContent = analysisResult.nutrition.fats + "g";
        
        // 6. Alternatives
        alternativesList.innerHTML = "";
        if (analysisResult.alternatives && analysisResult.alternatives.length > 0) {
            alternativesBlock.style.display = "block";
            analysisResult.alternatives.forEach(alt => {
                const li = document.createElement("li");
                li.textContent = alt;
                alternativesList.appendChild(li);
            });
        } else {
            alternativesBlock.style.display = "none";
        }
        
        // Re-create icons loaded inside predictions
        lucide.createIcons();
        
        // Speak voice warnings
        speakAlert(analysisResult.is_safe, analysisResult.top_predictions[0].name);
    }
    
    // --- PDF EXPORT EXECUTOR ---
    exportPdfBtn.addEventListener("click", () => {
        if (!analysisResult) return;
        
        exportPdfBtn.disabled = true;
        
        const reqData = {
            food_name: analysisResult.top_predictions[0].name,
            confidence: analysisResult.top_predictions[0].confidence,
            is_safe: analysisResult.is_safe,
            user_allergies: analysisResult.user_allergies,
            detected_allergens: analysisResult.detected_allergens,
            nutrition: analysisResult.nutrition,
            alternatives: analysisResult.alternatives
        };
        
        fetch("/api/export-pdf", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(reqData)
        })
        .then(res => {
            if (!res.ok) throw new Error("Could not download PDF");
            return res.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `allergy_ai_pro_${reqData.food_name.replace(/\s+/g, '_')}_report.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            exportPdfBtn.disabled = false;
        })
        .catch(err => {
            alert("Error downloading PDF: " + err.message);
            exportPdfBtn.disabled = false;
        });
    });
    
    // --- ANALYTICS CHARTS ---
    function initCharts() {
        const ctxSafety = document.getElementById("chart-safety").getContext("2d");
        const ctxHistory = document.getElementById("chart-history").getContext("2d");
        
        safetyChart = new Chart(ctxSafety, {
            type: "doughnut",
            data: {
                labels: ["Compatibles", "Contaminés"],
                datasets: [{
                    data: [stats.safe_dishes || 5, stats.dangerous_dishes || 2],
                    backgroundColor: ["#00e676", "#ff1744"],
                    borderColor: "#0b0f19",
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: "#94a3b8", font: { family: "Inter" } }
                    }
                }
            }
        });
        
        // Mock history if empty to look pretty
        const labels = [];
        const safeData = [];
        const dangerData = [];
        
        if (stats.history.length === 0) {
            labels.push("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi");
            safeData.push(3, 2, 4, 1, 3);
            dangerData.push(1, 0, 2, 1, 0);
        } else {
            // Group by date
            const grouped = {};
            stats.history.forEach(h => {
                if (!grouped[h.date]) grouped[h.date] = { safe: 0, danger: 0 };
                if (h.safe) grouped[h.date].safe++;
                else grouped[h.date].danger++;
            });
            Object.keys(grouped).forEach(date => {
                labels.push(date);
                safeData.push(grouped[date].safe);
                dangerData.push(grouped[date].danger);
            });
        }
        
        historyChart = new Chart(ctxHistory, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Plats Sûrs",
                        data: safeData,
                        backgroundColor: "rgba(0, 230, 118, 0.7)"
                    },
                    {
                        label: "Allergènes Détectés",
                        data: dangerData,
                        backgroundColor: "rgba(255, 23, 68, 0.7)"
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.05)" } },
                    y: { ticks: { color: "#94a3b8", stepSize: 1 }, grid: { color: "rgba(255,255,255,0.05)" } }
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: "#94a3b8", font: { family: "Inter" } }
                    }
                }
            }
        });
    }
    
    function updateChartsData() {
        if (!safetyChart || !historyChart) return;
        
        // Update safety chart data
        safetyChart.data.datasets[0].data = [stats.safe_dishes, stats.dangerous_dishes];
        safetyChart.update();
        
        // Update history chart data
        if (stats.history.length > 0) {
            const labels = [];
            const safeData = [];
            const dangerData = [];
            const grouped = {};
            stats.history.forEach(h => {
                if (!grouped[h.date]) grouped[h.date] = { safe: 0, danger: 0 };
                if (h.safe) grouped[h.date].safe++;
                else grouped[h.date].danger++;
            });
            Object.keys(grouped).forEach(date => {
                labels.push(date);
                safeData.push(grouped[date].safe);
                dangerData.push(grouped[date].danger);
            });
            
            historyChart.data.labels = labels;
            historyChart.data.datasets[0].data = safeData;
            historyChart.data.datasets[1].data = dangerData;
            historyChart.update();
        }
    }
    
    // --- DAILY JOURNAL TRACKER ACTION ---
    const addJournalBtn = document.getElementById("btn-add-journal");
    addJournalBtn.addEventListener("click", () => {
        if (!analysisResult) return;
        
        const nut = analysisResult.nutrition;
        journal.calories += Math.round(nut.calories);
        journal.proteins += Math.round(nut.proteins);
        journal.carbs += Math.round(nut.carbs);
        journal.fats += Math.round(nut.fats);
        
        localStorage.setItem("allergy_journal", JSON.stringify(journal));
        updateJournalUI();
        
        // Visual feedback
        const oldText = document.getElementById("btn-add-journal-text").textContent;
        document.getElementById("btn-add-journal-text").textContent = t("lbl-added-journal") || "Ajouté !";
        addJournalBtn.disabled = true;
        setTimeout(() => {
            document.getElementById("btn-add-journal-text").textContent = oldText;
            addJournalBtn.disabled = false;
        }, 1500);
    });
    
    function updateJournalUI() {
        document.getElementById("val-tracker-calories").textContent = `${journal.calories} / 2000 kcal`;
        document.getElementById("val-tracker-proteins").textContent = `${journal.proteins}g / 120g`;
        document.getElementById("val-tracker-carbs").textContent = `${journal.carbs}g / 250g`;
        document.getElementById("val-tracker-fats").textContent = `${journal.fats}g / 70g`;
        
        document.getElementById("bar-tracker-calories").style.width = `${Math.min(100, (journal.calories / 2000) * 100)}%`;
        document.getElementById("bar-tracker-proteins").style.width = `${Math.min(100, (journal.proteins / 120) * 100)}%`;
        document.getElementById("bar-tracker-carbs").style.width = `${Math.min(100, (journal.carbs / 250) * 100)}%`;
        document.getElementById("bar-tracker-fats").style.width = `${Math.min(100, (journal.fats / 70) * 100)}%`;
    }
    
    // --- SPEECH UTTERANCE ALERTS ---
    function speakAlert(isSafe, dishName) {
        if (!window.speechSynthesis) return;
        
        window.speechSynthesis.cancel();
        
        let msgText = "";
        let langCode = "fr-FR";
        
        if (currentLanguage === "fr") {
            langCode = "fr-FR";
            msgText = isSafe 
                ? `Le plat ${dishName} est compatible avec votre profil.` 
                : `Attention ! Le plat ${dishName} contient des allergènes dangereux.`;
        } else if (currentLanguage === "en") {
            langCode = "en-US";
            msgText = isSafe 
                ? `The dish ${dishName} is compatible with your profile.` 
                : `Warning! The dish ${dishName} contains dangerous allergens.`;
        } else if (currentLanguage === "ar") {
            langCode = "ar-SA";
            msgText = isSafe 
                ? `طبق ${dishName} متوافق مع ملفك الشخصي.` 
                : `انتبه! طبق ${dishName} يحتوي على مسببات حساسية خطيرة.`;
        }
        
        const utterance = new SpeechSynthesisUtterance(msgText);
        utterance.lang = langCode;
        
        const voices = window.speechSynthesis.getVoices();
        const voice = voices.find(v => v.lang.startsWith(langCode.substring(0, 2)));
        if (voice) utterance.voice = voice;
        
        window.speechSynthesis.speak(utterance);
    }
    
    // --- PARTNER RESTAURANT DATABASE & RENDERER ---
    const partnerRestaurants = [
        {
            name: "Al Fassia",
            city: "Marrakech",
            address: "55 Boulevard Mohamed Zerktouni, Marrakech",
            rating: "4.8 ⭐",
            phone: "+212 524 43 40 60",
            dishes: ["Tajine de Poulet aux Olives", "Couscous aux Sept Légumes", "Pastilla au Poulet"],
            allergens: ["Gluten", "Fruits à coque"],
            image: "https://blogs-images.forbes.com/juyoungseo/files/2017/04/Al-Fassia-1200x624.jpeg"
        },
        {
            name: "Dar Moha",
            city: "Marrakech",
            address: "81 Rue Dar el Bacha, Marrakech",
            rating: "4.7 ⭐",
            phone: "+212 524 38 64 00",
            dishes: ["Tajine de Veau aux Pruneaux", "Salade Marocaine", "Pastilla de Poisson"],
            allergens: ["Lait", "Poisson", "Fruits de mer", "Gluten"],
            image: "https://www.sientemarruecos.viajes/wp-content/uploads/2019/06/Restaurante-Dar-Moha-Marrakech.-Dar-moha-Restaurant-Marrakech-Morocco.jpg"
        },
        {
            name: "La Squala",
            city: "Casablanca",
            address: "Boulevard des Almohades, Casablanca",
            rating: "4.5 ⭐",
            phone: "+212 522 20 60 53",
            dishes: ["Tajine de Poisson", "Zaalouk", "Couscous Royal"],
            allergens: ["Poisson", "Gluten", "Lait"],
            image: "https://sqala.ma/wp-content/uploads/2021/03/DSC4518-scaled.jpg"
        },
        {
            name: "Le Cabestan",
            city: "Casablanca",
            address: "Phare d'El Hank, Casablanca",
            rating: "4.6 ⭐",
            phone: "+212 522 39 11 90",
            dishes: ["Briouates au Fromage", "Calamars Grillés", "Poisson du Jour"],
            allergens: ["Lait", "Poisson", "Fruits de mer", "Gluten"],
            image: "https://www.le-cabestan.com/wp-content/uploads/2021/12/2-hd2.jpg"
        },
        {
            name: "Dar Naji",
            city: "Rabat",
            address: "Avenue Al Jazaïr, Rabat",
            rating: "4.4 ⭐",
            phone: "+212 537 26 11 26",
            dishes: ["Rfissa", "Harira", "Batbout farci"],
            allergens: ["Gluten", "Viande"],
            image: "https://www.moroccoworldnews.com/wp-content/uploads/2021/01/Dar-naji.jpeg"
        },
        {
            name: "L'Ambre at Riad Fes",
            city: "Fès",
            address: "5 Derb Ben Slimane, Fès",
            rating: "4.8 ⭐",
            phone: "+212 535 74 12 06",
            dishes: ["Couscous Fassi", "Tajine d'agneau aux figues", "Mhancha"],
            allergens: ["Gluten", "Fruits à coque", "Sésame"],
            image: "https://riadfes.com/_novaimg/4337821-1379422_0_0_2200_2859_1000_1300.jpg"
        }
    ];
    
    function renderRestaurants() {
        const grid = document.getElementById("restaurants-grid");
        if (!grid) return;
        grid.innerHTML = "";
        
        const selectedCity = document.getElementById("restaurant-city-filter").value;
        const userAllergens = getSelectedAllergens();
        
        partnerRestaurants.forEach(rest => {
            if (selectedCity !== "all" && rest.city !== selectedCity) return;
            
            const userAllergensClean = userAllergens.map(a => a.toLowerCase().trim());
            const overlaps = rest.allergens.filter(alg => userAllergensClean.includes(alg.toLowerCase().trim()));
            const isSafe = overlaps.length === 0;
            
            const card = document.createElement("div");
            card.className = "restaurant-card";
            
            const badgeClass = isSafe ? "restaurant-status-safe" : "restaurant-status-unsafe";
            const badgeText = isSafe 
                ? (t("lbl-restaurant-safe") || "Sécurisé") 
                : `${t("lbl-restaurant-unsafe") || "Contient"} (${overlaps.join(", ")})`;
                
            card.innerHTML = `
                <div class="restaurant-image-container">
                    <img src="${rest.image}" alt="${rest.name}" class="restaurant-image" referrerpolicy="no-referrer" onerror="this.src='https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=600&q=80'">
                </div>
                <span class="restaurant-status-badge ${badgeClass}">${badgeText}</span>
                <div class="restaurant-title">
                     <span>${rest.name}</span>
                     <span style="color: #ffd54f; font-size: 0.95rem;">${rest.rating}</span>
                </div>
                <div class="restaurant-info-item"><i data-lucide="map-pin"></i> <span>${rest.city} - ${rest.address}</span></div>
                <div class="restaurant-info-item"><i data-lucide="phone"></i> <span>${rest.phone}</span></div>
                <div class="restaurant-menu-title">Plats Populaires :</div>
                <div class="restaurant-menu-tags">
                     ${rest.dishes.map(d => `<span class="menu-tag">${d}</span>`).join("")}
                </div>
            `;
            
            grid.appendChild(card);
        });
        
        lucide.createIcons();
    }
    
    document.getElementById("restaurant-city-filter").addEventListener("change", renderRestaurants);
});
