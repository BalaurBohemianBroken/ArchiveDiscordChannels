const text_indent_amount = 15;
const loading_chunk_size = 1000;
const distance_to_load_chunk = 5000;
loaded_files = {}

current_archive_text = null;
archive_fully_loaded = true;  // True by default because there is no archive to load.
re_span = /(.+?<\/span>[\n\r]+)/gs;
loading_latch = false;  // Not sure this does anything in JS, not sure how setInterval works. But, for safety.

// ID'd elements. Filled on onload.
element_archive_content = null;
element_channel_selector = null;
element_button_load_all = null;

// TODO: Had some weird issues when loading archives one after another. Start was clipped. Investigate.
// TODO: Embed url loading

window.onload = function() {
    element_archive_content = document.getElementById("archive_content");
    element_channel_selector = document.getElementById("channel_selector");
    element_button_load_all = document.getElementById("button_load_all");

    add_archive_directory_listener();
    setInterval(update_loop, 500);
}

function update_loop() {
    // Hide/display "load all" button when necessary.
    if (archive_fully_loaded || loading_latch) {
        element_button_load_all.style.display = "none";
    }
    else {
        element_button_load_all.style.display = "block";
    }

    // If close to bottom, render more of the archive file
    if (!archive_fully_loaded) {
        var scroll_y = window.scrollY
        var page_height = (document.height !== undefined) ? document.height : document.body.offsetHeight;
        if (page_height - scroll_y <= distance_to_load_chunk) {
            load_archive_chunk(element_archive_content, current_archive_text, loading_chunk_size);
        }
    }
}

function add_archive_directory_listener() {
    var fileSelector = document.getElementById('archive_folder_picker');
    fileSelector.addEventListener('change', on_select_archive_directory)
}

function on_select_archive_directory(event) {
    reset_current_archive();

    var folder_structure = create_folder_structure(event.target.files);
    var root_folder = Object.keys(folder_structure)[0];
    read_archive_folder(folder_structure[root_folder], root_folder, root_folder, element_channel_selector, 0);
}

function create_folder_structure(files) {
    // Takes the list of files and their paths, and creates a json object of the structure.
    var folder_structure = {};
    for (let i = 0; i < files.length; i++) {
        let file = files[i];
        loaded_files[file.webkitRelativePath] = file;
        let paths = file.webkitRelativePath.split("/");
        folder_pos = folder_structure;
        for (let j = 0; j < paths.length; j++) {
            let path = paths[j];
            // Folder
            if (j != paths.length - 1) {
                if (!(path in folder_pos)) {
                    folder_pos[path] = {};
                }
                folder_pos = folder_pos[path];
            }
            // File
            else {
                if (!("!!files" in folder_pos)) {
                    folder_pos["!!files"] = [];
                }
                folder_pos["!!files"].push(path);
            }
        }
    }

    return folder_structure;
}

function read_archive_folder(folder_contents, folder_name, current_path, parent_element, indent_level) {
    var my_details = create_dropdown(folder_name, indent_level);
    parent_element.append(my_details);

    for (var entry in folder_contents) {
        if (entry == "!!files") {
            continue;
        }
        read_archive_folder(folder_contents[entry], entry, current_path + `/${entry}`, my_details, indent_level + 1);
    }

    if (!("!!files" in folder_contents))
        return;
    for (var file_name of folder_contents["!!files"]) {
        var extension = file_name.substring(file_name.length - 4)
        if (extension != "html")
            continue;
        my_details.append(create_archive_selector(file_name, current_path + `/${file_name}`, indent_level + 1));
    }
}

function create_dropdown(label, indent_level) {
    // Add relevant HTML to element; Return new container
    var details = document.createElement("details");
    details.classList.add("details_dropdown");
    details.classList.add("text");
    var indent = text_indent_amount * indent_level;
    details.innerHTML = `<summary style="text-indent: ${indent}px;">${label}</summary>`
    return details;
}

function create_archive_selector(label, file_path, indent_level) {
    // Add clickable loading thingy.
    var text_div = document.createElement("div");
    text_div.classList.add("archive_selector");
    var indent = text_indent_amount * indent_level;
    text_div.style.textIndent = `${indent}px`;
    text_div.innerHTML = `<span data-file_path="${file_path}" onclick="clicked_archive(this);">${label}</span>`
    return text_div;
}

// From: https://stackoverflow.com/a/196510
function clicked_archive(element) {
    reset_current_archive();

    var element_path = element.getAttribute("data-file_path");
    var archive_file = loaded_files[element_path];
    var reader = new FileReader();
    reader.onload = () => {
        loaded_archive(reader.result)
    };
    reader.readAsText(archive_file);
}

function loaded_archive(archive_content) {
    // This is pretty rough. But it should work with any modern archive files I make.
    var dummy = document.createElement("div");
    dummy.innerHTML = archive_content;
    current_archive_text = dummy.querySelector("p").innerHTML;

    var size_of_loaded = load_archive_chunk(element_archive_content, current_archive_text, loading_chunk_size);
    current_archive_text = current_archive_text.substring(size_of_loaded);
}

function load_archive_chunk(into, archive, chunk_size) {
    if (loading_latch) {
        console.warning("Tried to load new archive while already loading archive.")
        return;
    }
    loading_latch = true;
    // Load more messages.
    var chunks_loaded = 0;
    var chunk_loading = "";
    while (chunks_loaded < chunk_size && !archive_fully_loaded) {
        chunks_loaded += 1;
        var match = re_span.exec(archive);
        if (match == null) {
            archive_fully_loaded = true;
            break;
        }
        chunk_loading += match[0];
    }

    var chunk = document.createElement("div");
    chunk.classList.add("archive_chunk");
    chunk.innerHTML = chunk_loading;
    into.appendChild(chunk);
    loading_latch = false;
    return chunk_loading.length;
}

function load_archive_full() {
    var size_of_loaded = load_archive_chunk(element_archive_content, current_archive_text, 999999999);
    current_archive_text = current_archive_text.substring(size_of_loaded);
}

function reset_current_archive() {
    element_archive_content.innerHTML = "";
    current_archive_text = null;
    current_archive_position = 0;
    archive_fully_loaded = false;
}