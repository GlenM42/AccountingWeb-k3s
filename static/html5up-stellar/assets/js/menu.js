/* ==================================================================
   Solid-State slide-in drawer (stand-alone version for Stellar)
   ================================================================= */
(function ($) {

    // Run after the DOM is ready so #menu definitely exists.
    $(function () {

        var $body  = $('body'),
            $menu  = $('#menu');

        /* ---------- locking helpers (exactly as in Solid-State) --- */
        $menu._locked = false;

        $menu._lock = function () {
            if ($menu._locked) return false;
            $menu._locked = true;
            window.setTimeout(function () { $menu._locked = false; }, 350);
            return true;
        };

        $menu._show = function () {
            if ($menu._lock()) $body.addClass('is-menu-visible');
        };

        $menu._hide = function () {
            if ($menu._lock()) $body.removeClass('is-menu-visible');
        };

        $menu._toggle = function () {
            if ($menu._lock()) $body.toggleClass('is-menu-visible');
        };

        /* ---------- event wiring ---------------------------------- */
        $menu
            .appendTo($body)                     // just in case it isn't already
            .on('click', function (event) {
                event.stopPropagation();
                $menu._hide();                  // tap outside → close
            })
            .find('.inner')
                .on('click', '.close', function (event) {
                    event.preventDefault();
                    event.stopPropagation();
                    $menu._hide();
                })
                .on('click', function (event) {
                    event.stopPropagation();    // clicks inside drawer stay inside
                })
                .on('click', 'a', function (event) {
                    var href = $(this).attr('href');
                    event.preventDefault();
                    event.stopPropagation();
                    $menu._hide();
                    window.setTimeout(function () {
                        window.location.href = href;
                    }, 350);                    // match drawer animation
                });

        // “Menu” button in the header and Esc-key support
        $body
            .on('click', 'a[href="#menu"]', function (event) {
                event.preventDefault();
                event.stopPropagation();
                $menu._toggle();
            })
            .on('keydown', function (event) {
                if (event.keyCode === 27)       // Esc
                    $menu._hide();
            });

    });

})(jQuery);
