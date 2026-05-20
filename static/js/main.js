// Main JavaScript for SecondChance Connect

// Auto-hide alerts after 5 seconds
$(document).ready(function() {
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    // Like functionality with AJAX
    $('.like-btn').on('click', function(e) {
        e.preventDefault();
        var userId = $(this).data('user-id');
        var $btn = $(this);
        
        $.ajax({
            url: '/like/' + userId,
            method: 'POST',
            success: function(response) {
                if (response.mutual) {
                    $('#mutualModal').modal('show');
                    $btn.removeClass('btn-outline-primary').addClass('btn-success disabled');
                    $btn.html('<i class="fas fa-check"></i> Matched!');
                } else {
                    $btn.removeClass('btn-outline-primary').addClass('btn-primary disabled');
                    $btn.html('<i class="fas fa-heart"></i> Liked');
                }
            },
            error: function(xhr) {
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    alert(xhr.responseJSON.error);
                }
            }
        });
    });
    
    // Character counter for textareas
    $('textarea[maxlength]').on('input', function() {
        var max = $(this).attr('maxlength');
        var current = $(this).val().length;
        var remaining = max - current;
        
        var counter = $(this).siblings('.char-counter');
        if (counter.length === 0) {
            counter = $('<small class="char-counter text-muted"></small>');
            $(this).after(counter);
        }
        
        counter.text(remaining + ' characters remaining');
        
        if (remaining < 20) {
            counter.addClass('text-warning');
        } else {
            counter.removeClass('text-warning');
        }
        
        if (remaining < 0) {
            counter.addClass('text-danger');
        }
    });
    
    // Confirm delete actions
    $('.delete-confirm').on('click', function(e) {
        if (!confirm('Are you sure you want to delete this? This action cannot be undone.')) {
            e.preventDefault();
        }
    });
    
    // Auto-refresh messages on messages page
    if ($('#messages-container').length) {
        setInterval(function() {
            location.reload();
        }, 30000); // Refresh every 30 seconds
    }
    
    // Search form validation
    $('form.search-form').on('submit', function(e) {
        var query = $(this).find('input[name="q"]').val();
        if (query.length < 2 && query.length > 0) {
            e.preventDefault();
            alert('Please enter at least 2 characters for search');
        }
    });
    
    // Smooth scroll to top
    $('#scroll-top').on('click', function() {
        $('html, body').animate({ scrollTop: 0 }, 'smooth');
    });
    
    // Show scroll to top button
    $(window).on('scroll', function() {
        if ($(this).scrollTop() > 200) {
            $('#scroll-top').fadeIn();
        } else {
            $('#scroll-top').fadeOut();
        }
    });
});

// Mutual match notification
function showMatchNotification(otherUserName) {
    if (Notification.permission === "granted") {
        new Notification("It's a match!", {
            body: "You have a new match with " + otherUserName + "!",
            icon: "/static/images/heart-icon.png"
        });
    }
}

// Request notification permission
if (Notification.permission !== "granted" && Notification.permission !== "denied") {
    Notification.requestPermission();
}