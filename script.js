const subjectsData = {
    'GCSE': ['French', 'Spanish', 'German', 'Mandarin', 'Geography', 'History', 'Computer Science', 'Music', 'Drama', 'Art', 'Latin', 'Sports Studies', 'Business'],
    'A Level': ['Maths', 'Further Maths', 'Physics', 'Chemistry', 'Biology', 'Music', 'German', 'French', 'Psychology', 'History', 'Geography', 'Economics', 'English', 'Art']
};

let selectedSubjects = [];
let subjectDetails = {};
let userInstruments = [];

const defaultLessonColours = {
    "Maths": "#4080FF",
    "English": "#FFFF00",
    "Geography": "#20C040",
    "RPE": "#E04040",
    "Computer Science": "#C060C0",
    "Physics": "#FF80C0",
    "PE": "#FF8000",
    "German": "#80FF00",
    "Music": "#123456",
    "PSHE": "#707070",
    "Biology": "#006000",
    "Chemistry": "#0000C0"
};

function updateColourPreferences() {
    const colourList = document.getElementById('colourList');
    if (!colourList) return;
    const mandatory = getMandatorySubjects();
    const allSubjects = [...new Set([...mandatory, ...selectedSubjects])];
    colourList.innerHTML = '';
    
    allSubjects.forEach(subj => {
        const div = document.createElement('div');
        div.className = 'subject-item';
        div.style.justifyContent = 'space-between';
        
        // Use the hex from your file if it exists, otherwise default to green
        const defaultHex = defaultLessonColours[subj] || "#00ff00";
        
        div.innerHTML = `
            <label for="color-${subj}">${subj}</label>
            <input type="color" id="color-${subj}" name="color-${subj}" value="${defaultHex}">
        `;
        colourList.appendChild(div);
    });
}

const updateSelectedArray = () => {
    const list = document.getElementById('subjectList');
    if (!list) return;
    selectedSubjects = Array.from(list.querySelectorAll('input:checked')).map(cb => cb.value);
    generateTimetable('timetableBodyA');
    generateTimetable('timetableBodyB');
    updateColourPreferences();
};

function getMandatorySubjects() {
    const radio = document.querySelector('input[name="school_level"]:checked');
    const level = radio ? radio.value : '';
    if (level === 'GCSE') {
        return ['Maths', 'English', 'RPE', 'PE', 'Physics', 'Chemistry', 'Biology', 'PSHE'];
    } else if (level === 'A Level') {
        return ['Games'];
    }
    return [];
}

function updateColourPreferences() {
    const colourList = document.getElementById('colourList');
    if (!colourList) return;
    const mandatory = getMandatorySubjects();
    const allSubjects = [...new Set([...mandatory, ...selectedSubjects])];
    colourList.innerHTML = '';
    allSubjects.forEach(subj => {
        const div = document.createElement('div');
        div.className = 'subject-item';
        div.style.justifyContent = 'space-between';
        div.innerHTML = `
            <label for="color-${subj}">${subj}</label>
            <input type="color" id="color-${subj}" name="color-${subj}" value="#00ff00">
        `;
        colourList.appendChild(div);
    });
}

function generateTimetable(targetId) {
    const tbody = document.getElementById(targetId);
    if (!tbody) return;
    
    const mandatory = getMandatorySubjects();
    const periods = ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5"];
    tbody.innerHTML = '';

    periods.forEach(period => {
        const row = document.createElement('tr');
        const periodCell = document.createElement('td');
        periodCell.innerHTML = `<strong>${period}</strong>`;
        row.appendChild(periodCell);

        for (let i = 1; i <= 5; i++) {
            const td = document.createElement('td');
            const select = document.createElement('select');
            select.className = "timetable-select";
            select.innerHTML = `<option value="">Free</option>`;
            
            const combinedSubjects = [...selectedSubjects, ...mandatory];
            combinedSubjects.forEach(subj => {
                const opt = document.createElement('option');
                opt.value = subj;
                opt.textContent = subj;
                select.appendChild(opt);
            });

            const roomInput = document.createElement('input');
            roomInput.type = 'text';
            roomInput.placeholder = 'Room';
            roomInput.className = 'timetable-input';

            const teacherInput = document.createElement('input');
            teacherInput.type = 'text';
            teacherInput.placeholder = 'TCH';
            teacherInput.maxLength = 3;
            teacherInput.className = 'timetable-input';

            select.addEventListener('change', () => {
                const val = select.value;
                if (val && subjectDetails[val]) {
                    if (!roomInput.value) roomInput.value = subjectDetails[val].room || '';
                    if (!teacherInput.value) teacherInput.value = subjectDetails[val].teacher || '';
                }
            });

            const updateData = () => {
                const val = select.value;
                if (val) {
                    subjectDetails[val] = {
                        room: roomInput.value,
                        teacher: teacherInput.value
                    };
                    autoFillBlankCells(val);
                }
            };

            roomInput.addEventListener('input', updateData);
            teacherInput.addEventListener('input', updateData);

            td.appendChild(select);
            td.appendChild(roomInput);
            td.appendChild(teacherInput);
            row.appendChild(td);
        }
        tbody.appendChild(row);
    });
}

function autoFillBlankCells(subjectName) {
    const allSelects = document.querySelectorAll('.timetable-select');
    allSelects.forEach(select => {
        if (select.value === subjectName) {
            const td = select.parentElement;
            const inputs = td.querySelectorAll('.timetable-input');
            const roomIn = inputs[0];
            const techIn = inputs[1];

            if (!roomIn.value) roomIn.value = subjectDetails[subjectName].room;
            if (!techIn.value) techIn.value = subjectDetails[subjectName].teacher;
        }
    });
}

function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    const activeTab = document.getElementById(tabName);
    if (activeTab) {
        activeTab.style.display = "flex";
    }
    if (evt && evt.currentTarget) {
        evt.currentTarget.className += " active";
    }
}

function updateSubjects() {
    const container = document.getElementById('subjectContainer');
    const list = document.getElementById('subjectList');
    const radio = document.querySelector('input[name="school_level"]:checked');
    if (!radio) return;
    const selectedLevel = radio.value;
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    list.innerHTML = '';
    
    let subjectsToShow = [...subjectsData[selectedLevel]];
    if (selectedLevel === 'A Level') {
        subjectsToShow.push('EPQ');
    }

    subjectsToShow.forEach(subject => {
        const div = document.createElement('div');
        div.className = 'subject-item';
        div.innerHTML = `<input type="checkbox" name="subj" value="${subject}" id="${subject}"><label for="${subject}">${subject}</label>`;
        list.appendChild(div);
        
        const checkbox = div.querySelector('input');
        checkbox.addEventListener('change', () => {
            const checkedCheckboxes = list.querySelectorAll('input:checked');
            const checkedValues = Array.from(checkedCheckboxes).map(c => c.value);
            const checkedCount = checkedCheckboxes.length;
            const statusBar = document.getElementById('status');
            const submitBtn = document.getElementById('submitBtn');

            if (selectedLevel === 'GCSE') {
                if (checkedCount > 4) {
                    checkbox.checked = false;
                    alert("You can only pick 4 subjects at GCSE.");
                }
            } else if (selectedLevel === 'A Level') {
                const hasFurtherMaths = checkedValues.includes('Further Maths');
                const hasEPQ = checkedValues.includes('EPQ');
                
                if (checkedCount === 4 && !hasFurtherMaths && !hasEPQ) {
                    checkbox.checked = false;
                    alert("To take 4 A-Levels, one must be Further Maths, or you must take an EPQ.");
                } else if (checkedCount > 4) {
                    checkbox.checked = false;
                    alert("You cannot select more than 4 subjects.");
                }
            }

            const finalCount = list.querySelectorAll('input:checked').length;
            const targetCount = (selectedLevel === 'GCSE') ? 4 : 3; 
            
            if(statusBar) statusBar.textContent = `Selected: ${finalCount}`;
            if(submitBtn) {
                if (selectedLevel === 'GCSE') {
                    submitBtn.disabled = (finalCount !== 4);
                } else {
                    submitBtn.disabled = (finalCount < 3);
                }
            }
        });
    });
    updateColourPreferences();
}

function setupMusicLessons() {
    const addBtn = document.getElementById('addInstrumentBtn');
    const saveBtn = document.getElementById('saveMusicBtn');
    const container = document.getElementById('instrumentContainer');

    if (addBtn) {
        addBtn.addEventListener('click', () => {
            const currentEntries = container.querySelectorAll('.instrument-entry');
            if (currentEntries.length < 2) {
                const newDiv = document.createElement('div');
                newDiv.className = 'instrument-entry';
                newDiv.innerHTML = `
                    <input type="text" class="timetable-input instrument-input" placeholder="e.g. Piano">
                    <button type="button" class="remove-btn" title="Remove">✕</button>
                `;
                
                container.appendChild(newDiv);

                newDiv.querySelector('.remove-btn').addEventListener('click', () => {
                    newDiv.remove();
                    addBtn.style.display = 'block';
                });

                if (container.querySelectorAll('.instrument-entry').length >= 2) {
                    addBtn.style.display = 'none';
                }
            }
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            const inputs = container.querySelectorAll('.instrument-input');
            userInstruments = Array.from(inputs)
                .map(input => input.value.trim())
                .filter(val => val !== "");
            
        });
    }
}

function extractTableData(tbodyId, type) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return [];
    
    let columns = [[], [], [], [], []]; // Representing Monday to Friday
    const rows = tbody.querySelectorAll('tr');
    
    rows.forEach(row => {
        const cells = Array.from(row.querySelectorAll('td')).slice(1); // Skip Period header
        cells.forEach((td, index) => {
            if (type === 'subject') {
                columns[index].push(td.querySelector('select').value || "Free");
            } else if (type === 'room') {
                columns[index].push(td.querySelectorAll('input')[0].value || "");
            } else if (type === 'teacher') {
                columns[index].push(td.querySelectorAll('input')[1].value || "");
            }
        });
    });
    return columns;
}

function saveSettingsFile() {
    // Validation: Check if a school level is selected
    if (!document.querySelector('input[name="school_level"]:checked')) {
        alert("Please select a school level in the Subjects tab first.");
        return;
    }

    // Capture Lesson Colours
    const lessonColours = {};
    const colourInputs = document.querySelectorAll('#colourList input[type="color"]');
    colourInputs.forEach(input => {
        const subject = input.name.replace('color-', '');
        lessonColours[subject] = input.value;
    });

    // Capture Music Lessons
    const music = {};
    userInstruments.forEach(inst => {
        music[inst] = "2026-01-01T00:00:00";
    });

    // Compile the full object using your template
    const settingsData = {
        "barsize": [600, 25],
        "animation": 0,
        "sounds": 0,
        "themes": [/* Your themes array from the provided JSON */],
        "theme": 0,
        "lessontimes": {
            "monFri": [[8, 45, 25], [9, 10, 60], [10, 25, 60], [11, 30, 60], [12, 30, 55], [13, 25, 60], [14, 35, 60]],
            "tueThu": [[8, 45, 5], [8, 50, 60], [10, 5, 60], [11, 10, 60], [12, 10, 25], [12, 35, 50], [13, 25, 60], [14, 35, 60]]
        },
        "lessonnames": ["Registration", "Period 1", "Period 2", "Period 3", "Lunch", "Period 4", "Period 5"],
        "menucolours": ["#FF9933", "#00CC99", "#9966FF", "#969696", "#CC66FF", "#A9D8FF", "#66FFFF", "#FF9966", "#A2D762", "#FF66CC", "#FFFF66", "#FF5050"],
        "lessoncolours": lessonColours,
        "timetable-a": extractTableData('timetableBodyA', 'subject'),
        "timetable-b": extractTableData('timetableBodyB', 'subject'),
        "rooms-a": extractTableData('timetableBodyA', 'room'),
        "rooms-b": extractTableData('timetableBodyB', 'room'),
        "teachers-a": extractTableData('timetableBodyA', 'teacher'),
        "teachers-b": extractTableData('timetableBodyB', 'teacher'),
        "week": 0,
        "music": music,
        "common-chars": ["b0", "2192", "df", "d7", "f7", "3c0"],
        "dnd": 0,
        "unit": 1
    };

    // Create and trigger download
    const blob = new Blob([JSON.stringify(settingsData, null, 4)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = "settings.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

document.addEventListener('DOMContentLoaded', () => {
    const defaultTab = document.getElementById("defaultOpen");
    if (defaultTab) defaultTab.click();
    setupMusicLessons();
    updateColourPreferences();
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', () => {
            updateSelectedArray();
        });
    }
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', saveSettingsFile);
    }
});
