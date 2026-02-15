const text_indent_amount = 15;
loaded_files = {}
const parse_html_archive = /(.*?)<p>/gs;
const archive_clip_from_end = "</body></html>"

// TODO: Chunking loading
// TODO: Embed url loading

window.onload = function() {
    add_archive_directory_listener()
}

function add_archive_directory_listener() {
    var fileSelector = document.getElementById('archive_folder_picker');
    fileSelector.addEventListener('change', on_select_archive_directory)
}

function on_select_archive_directory(event) {
    var channel_selector = document.getElementById("channel_selector");

    // Remove old structure
    channel_selector.innerHTML = "";

    var folder_structure = create_folder_structure(event.target.files);
    var root_folder = Object.keys(folder_structure)[0];
    read_archive_folder(folder_structure[root_folder], root_folder, root_folder, channel_selector, 0);
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
    document.getElementById("archive_content").innerHTML = "";
    var element_path = element.getAttribute("data-file_path");
    var archive_file = loaded_files[element_path];
    var reader = new FileReader();
    reader.onload = () => {
        loaded_archive(reader.result)
    };
    reader.readAsText(archive_file);
}

function loaded_archive(archive_content) {
    document.getElementById("archive_content").innerHTML = archive_content;
}