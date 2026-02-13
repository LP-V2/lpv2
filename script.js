// 1. GLOBAL DATA: Accessible by all functions
const subjectsData = {
    'GCSE': ['French', 'Spanish', 'German', 'Mandarin', 'Geography', 'History', 'Computer Science', 'Music', 'Drama', 'Latin', 'Sports Studies', 'Business'],
    'A Level': ['Maths', 'Further Maths', 'Physics', 'Music', 'German', 'French']
};

// 2. TAB LOGIC: Controls switching between Subjects, Colours, and Timetable
function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    
    // Hide all tab content
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }

    // Deactivate all tab buttons
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    // Show current tab as FLEX (to keep your 'gap' working!)
    const activeTab = document.getElementById(tabName);
    if (activeTab) {
        activeTab.style.display = "flex";
    }
    
    // Add active class to button
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

    // Reveal the subject selection box
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    list.innerHTML = '';

    // Generate checkboxes from the data at the top
    subjectsData[selectedLevel].forEach(subject => {
        const div = document.createElement('div');
        div.className = 'subject-item';
        div.innerHTML = `
            <input type="checkbox" name="subj" value="${subject}" id="${subject}">
            <label for="${subject}">${subject}</label>
        `;
        list.appendChild(div);

        // Add the selection limit logic to each new checkbox
        const checkbox = div.querySelector('input');
        checkbox.addEventListener('change', () => {
        const checkedCount = list.querySelectorAll('input:checked').length;
        const statusBar = document.getElementById('status');
        const submitBtn = document.getElementById('submitBtn');
    
        const targetCount = 4;

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
}

document.addEventListener('DOMContentLoaded', () => {
    const defaultTab = document.getElementById("defaultOpen");
    if (defaultTab) {
        defaultTab.click();
    } else {
        console.error("Could not find the button with id='defaultOpen'");
    }
});
