import $ from "jquery";

document.addEventListener('DOMContentLoaded', () => {
    $('#prompt-form').on('submit', (event: JQuery.SubmitEvent) => {
        event.preventDefault();
        const formData: string = $('#prompt-form').serialize();
    
        $.ajax({
            type: 'POST',
            url: '/',
            data: formData,
            success: (response: string) => {
                $('#result-section').html(response);
            }
        });
    });
});

function updateCharacterCount(): void {
    const promptInput = document.getElementById("prompt") as HTMLInputElement;
    const charCount: number = promptInput.value.length;
    const charCountDisplay = document.getElementById("charCount") as HTMLDivElement;
    charCountDisplay.textContent = `${charCount} / 4000`;
}

function updateStyleDescription(): void {
    const styleInput = document.getElementById("style") as HTMLSelectElement;
    const currentStyle: string = styleInput.value;
    const styleDescriptionDisplay = document.getElementById("styleDescription") as HTMLDivElement;

    if (currentStyle === "vivid") {
        styleDescriptionDisplay.textContent = "(Vivid causes the model to lean towards generating hyper-real and dramatic images)";
    } else if (currentStyle === "natural") {
        styleDescriptionDisplay.textContent = "(Natural causes the model to produce more natural, less hyper-real looking images)";
    }
}

function openTab(evt: MouseEvent, tabName: string): void {
    const tabcontent = Array.from(document.getElementsByClassName("tabcontent") as HTMLCollectionOf<HTMLElement>);
    tabcontent.forEach(element => element.style.display = "none");

    const tablinks = Array.from(document.getElementsByClassName("tablinks") as HTMLCollectionOf<HTMLElement>);
    tablinks.forEach(element => element.className = element.className.replace(" active", ""));

    const tab = document.getElementById(tabName) as HTMLElement;
    tab.style.display = "block";
    (evt.currentTarget as HTMLElement).className += " active";

    if (tabName === "GridView") {
        gridTabLoaded();
    }
}

// Set the default open tab (Generation tab)
(document.getElementById("defaultOpen") as HTMLElement).click();

let currentPage: number = 0;
let totalPages: number = -1;

function gridTabLoaded(): void {
    $.get('/get-total-pages', (data: string) => {
        totalPages = parseInt(data, 10);
        loadImages(currentPage);
    });
}

function loadImages(page: number): void {
    $.getJSON(`/get-images/${page}`, (data: string[]) => {
        const grid = $('.image-grid');
        grid.empty(); // Clear existing images

        data.forEach((image: string) => {
            const imgElement = $('<img>').attr('src', image);
            grid.append(imgElement);
        });
        document.getElementById("gridPageNum")!.textContent = `Page ${page + 1}/${totalPages + 1}`;
    });
}

function nextGrid(): void {
    currentPage += 1;
    loadImages(currentPage);
}

function previousGrid(): void {
    if (currentPage > 0) {
        currentPage -= 1;
        loadImages(currentPage);
    }
}

function openModal(src: string): void {
    document.getElementById('image-modal')!.style.display = "block";
    (document.getElementById('modal-image') as HTMLImageElement).src = src;
}

function closeModal(): void {
    document.getElementById('image-modal')!.style.display = "none";
}

document.getElementById('image-modal')!.addEventListener('wheel', (event: WheelEvent) => {
    event.preventDefault(); // Prevent background scrolling when the modal is open
});

document.getElementById('modal-image')!.addEventListener('wheel', (event: WheelEvent) => {
    const img = event.target as HTMLImageElement;
    const scaleIncrement: number = 0.1;
    const currentScale = img.style.transform.match(/scale\(([^)]+)\)/);

    let scale: number = currentScale ? parseFloat(currentScale[1]) : 1;

    if (event.deltaY < 0) {
        scale += scaleIncrement; // Zoom in
    } else {
        scale -= scaleIncrement; // Zoom out
    }

    scale = Math.max(1, Math.min(scale, 5)); // Adjust min and max scale as needed
    img.style.transform = `scale(${scale})`;
});
