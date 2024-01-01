document.addEventListener('DOMContentLoaded', () => {
    $('#loading-spinner').hide();
    $('#prompt-form').on('submit', (event: JQuery.SubmitEvent) => {
        event.preventDefault();
        const formData: string = $('#prompt-form').serialize();
        
        $('#loading-spinner').show();
    
        $.ajax({
            type: 'POST',
            url: '/',
            data: formData,
            success: (response: string) => {
                $('#result-section').html(response);

                addEventListenerToElement("generatedImage", "click", openGenModal);
                addEventListenerToElement("generatedImageClose", "click", closeGenModal);
                $('#loading-spinner').hide();
            }
        });
    });

    
    // Assigning event listeners
    addEventListenerToElement("generationTab", "click", handleTabClick);
    addEventListenerToElement("gridViewTab", "click", handleTabClick);
    addEventListenerToElement("style", "input", updateStyleDescription);
    addEventListenerToElement("prompt", "input", updateCharacterCount);
    
    // Grid buttons
    addEventListenerToElement("firstGrid", "click", firstGrid);
    addEventListenerToElement("previousGrid", "click", previousGrid);
    addEventListenerToElement("nextGrid", "click", nextGrid);
    addEventListenerToElement("lastGrid", "click", lastGrid);

    // Grid Modal Buttons
    addEventListenerToElement("grid-image-close", "click", closeGridModal);

    document.getElementById("generationTab")!.click();
});

// Function to add an event listener to an element
function addEventListenerToElement(elementId: string, eventType: string, handler: (evt: Event) => void) {
    const element = document.getElementById(elementId);
    if (element) {
        element.addEventListener(eventType, handler);
    } else {
        console.warn(`Element with ID '${elementId}' not found.`);
    }
}

type TabId = 'generationTab' | 'gridViewTab';

// Event Handlers
function handleTabClick(evt: Event) {
    const element = evt.target as HTMLElement;
    const elementId = element.id as TabId;

    const tabMap: Record<TabId, string> = {
        "generationTab": "Generation",
        "gridViewTab": "GridView"
    };

    if (tabMap[elementId]) {
        openTab(evt as MouseEvent, tabMap[elementId]);
    }
}

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
            const imgElement = $('<img>').attr('src', image).attr('id', "gridImage");
            imgElement.on("click", openGridModal)
            grid.append(imgElement);
        });
        document.getElementsByTagName
        document.getElementById("gridPageNum")!.textContent = `Page ${page + 1}/${totalPages + 1}`;
    });
}

function firstGrid(): void {
    currentPage = 0;
    loadImages(currentPage);
}

function nextGrid(): void {
    if (currentPage < totalPages)
    {
        currentPage += 1;
        loadImages(currentPage);
    }
}

function previousGrid(): void {
    if (currentPage > 0) {
        currentPage -= 1;
        loadImages(currentPage);
    }
}

function lastGrid(): void {
    currentPage = totalPages;
    loadImages(currentPage);
}

function openGenModal(evt: Event): void {
    const src = (evt.currentTarget as HTMLImageElement).src
    document.getElementById('image-modal')!.style.display = "block";
    (document.getElementById('modal-image') as HTMLImageElement).src = src;

    document.getElementById('image-modal')!.addEventListener('wheel', (event: WheelEvent) => {
        event.preventDefault(); // Prevent background scrolling when the    modal is open
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
}

function openGridModal(evt: Event): void {
    const filePath = (evt.currentTarget as HTMLImageElement).src
    document.getElementById('grid-image-modal')!.style.display = "block";
    
    const thumbFileName = filePath.split('/').pop();
    const pathDir = filePath.slice(0, -(thumbFileName?.length ?? 0))
    const fileName = thumbFileName?.slice(0,-(".thumb.jpg".length)).concat(".png");
    (document.getElementById('grid-modal-image') as HTMLImageElement).src = pathDir + fileName;

    $.getJSON('/get-image-metadata/' + fileName, function(metadata) {
        var metadataDiv = document.getElementById('grid-info-panel') as HTMLElement;
        metadataDiv.innerHTML = ''; // Clear previous metadata
        for (var key in metadata) {
            // <div class="info-item"><span>Prompt:</span><span id="prompt-value"></span></div>
            var infoItem = document.createElement('div');
            infoItem.className = "info-item";
            infoItem.textContent = key + ":";
            metadataDiv.appendChild(infoItem);
            var infoValue = document.createElement('div');
            infoValue.className = "prompt-value";
            infoValue.textContent = metadata[key];
            metadataDiv.appendChild(infoValue);
        }
    });
}

function closeGenModal(): void {
    document.getElementById('image-modal')!.style.display = "none";
}

function closeGridModal(): void {
    document.getElementById('grid-image-modal')!.style.display = "none";
}