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
            '<iframe name="dummyframe3" id="dummyframe3" style="display: none;"></iframe>' +
            '<form action="/parse" target="dummyframe3" id="parseform" method="post"><input value="' + msg.id + '" hidden name="id">' +
            '<li><button type="submit" class="dropdown-item rounded-top">Спарсить участников</button></li>' +
            '</form>' +
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

socket.on('show_code', function(msg) {
var elem = document.getElementById('smsgroup')
elem.hidden=false;
var elem2 = document.getElementById('smsbutton')
elem2.innerHTML = 'Войти'
});

socket.on('reboot_page', function(msg) {
   window.location.reload();
});

socket.on('clear_all', function() {
var elem = document.getElementById('chatcount')
var elem2 = document.getElementById('chatcount2')
var elem3 = document.getElementById('usercount')
var elem4 = document.getElementById('usercount2')
elem.innerHTML = 0;
elem2.innerHTML = 0;
elem3.innerHTML = 0;
elem4.innerHTML = 0;
$('#tabledbody').empty()
});


socket.on('total_chats', function(msg) {
var elem = document.getElementById('chatcount')
var elem2 = document.getElementById('chatcount2')
elem.innerHTML = msg.count;
elem2.innerHTML = msg.count;
});

socket.on('total_users', function(msg) {
var elem = document.getElementById('usercount')
var elem2 = document.getElementById('usercount2')
elem.innerHTML = msg.count;
elem2.innerHTML = msg.count;
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

socket.on('updateprogresstext', function(msg) {
                    $('#progresstext').html(msg.text);
            });

socket.on('sendnotyferror', function(msg) {
var notyfDemo = new Notyf();
                    notyfDemo.error(msg.text)
            });
socket.on('sendnotyfsuccess', function(msg) {
var notyfDemo = new Notyf();
                    notyfDemo.success(msg.text)
            });

socket.on('updateprogress', function(msg) {
                    $('#progre').css('width', msg.percent + '%');
                    $('#progresspercent').html(msg.sended + '/' + msg.total);
            });