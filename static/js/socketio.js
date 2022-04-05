var socket = io('/');
socket.on('parsed_chat', function(msg) {
            $(tabled).append('<tr>' +
            '<td> <a class="fw-bold">' + msg.id + '</a> </td>' +
            '<td> <span>' + msg.title + '</span> </td>' +
            '<td> <span class="fw-normal">' + msg.access_hash + '</span> </td>' +
            '<td><a href="https://t.me/' + msg.username + '" target="_blank" class="fw-bold">' + msg.username + '</a></td>' +
            '<td>' + msg.participants_count + '</td>' +
            '<td>' +
            '<div class="dropdown me-1">' +
            '<button type="button" class="btn btn-secondary dropdown-toggle" id="dropdownMenuOffset" data-bs-toggle="dropdown" aria-expanded="false" data-bs-offset="-10,-40">' +
            'Действие' +
            '</button>' +
            '<ul class="dropdown-menu py-0" aria-labelledby="dropdownMenuOffset">' +
            '<li><button class="dropdown-item rounded-top">Спарсить участников</button></li>' +
            '<li><button data-bs-toggle="modal" data-bs-target="#deleteModal" data-val="' + msg.id +'" data-desc="' + msg.title + '" class="dropdown-item rounded-bottom">Удалить</button></li>' +
            '</ul>' +
            '</div>' +
            '</td>'
            + '</tr>');
            try {
                        $(norec).hide()
            } catch (e) {
            var a = e;
            }
});

socket.on('found_users', function(msg) {
try {
var elem = document.getElementById('swal2-html-container')
elem.innerHTML = 'Пользователей сохранено: ' + msg.count;
} catch {
var a = '';
}

})

socket.on('found_chats', function(msg) {
var elem = document.getElementById('swal2-html-container')
elem.innerHTML = 'Чатов найдено: ' + msg.count;
});

socket.on('show_message', function(msg) {
try {
Swal.fire({
          icon: msg.status,
          title: msg.title,
          text: msg.text,
          showConfirmButton: false
          })
} catch {
var a = ''
}

})