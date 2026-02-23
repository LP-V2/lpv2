const subjectsData = {
    'GCSE': ['French', 'Spanish', 'German', 'Mandarin', 'Geography', 'History', 'Computer Science', 'Music', 'Drama', 'Latin', 'Sports Studies', 'Business'],
    'A Level': ['Maths', 'Further Maths', 'Physics', 'Music', 'German', 'French']
};

let selectedSubjects = [];

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

            td.appendChild(select);
            td.appendChild(roomInput);
            td.appendChild(teacherInput);
            row.appendChild(td);
        }
        tbody.appendChild(row);
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
    
    subjectsData[selectedLevel].forEach(subject => {
        const div = document.createElement('div');
        div.className = 'subject-item';
        div.innerHTML = `<input type="checkbox" name="subj" value="${subject}" id="${subject}"><label for="${subject}">${subject}</label>`;
        list.appendChild(div);
        const checkbox = div.querySelector('input');
        checkbox.addEventListener('change', () => {
            const checkedCount = list.querySelectorAll('input:checked').length;
            const statusBar = document.getElementById('status');
            const submitBtn = document.getElementById('submitBtn');
            const targetCount = (selectedLevel === 'GCSE') ? 4 : 3;
            if (checkedCount > targetCount) {
                checkbox.checked = false;
                alert(`You can only pick ${targetCount} subjects.`);
            } else {
                if(statusBar) statusBar.textContent = `Selected: ${list.querySelectorAll('input:checked').length} / ${targetCount}`;
                if(submitBtn) {
                    submitBtn.disabled = (list.querySelectorAll('input:checked').length !== targetCount);
                }
            }
        });
    });
    updateColourPreferences();
}

document.addEventListener('DOMContentLoaded', () => {
    const defaultTab = document.getElementById("defaultOpen");
    if (defaultTab) defaultTab.click();
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', () => {
            updateSelectedArray();
        });
    }
});
