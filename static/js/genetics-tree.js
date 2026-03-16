(function() {
    var svg = document.getElementById('genetics-svg');
    if (!svg) return;

    var parentsEl = document.getElementById('genetics-parents');
    var tree = document.getElementById('genetics-tree');
    var parentNodes = parentsEl.querySelectorAll('.sd-genetics__node');
    var childNode = tree.querySelector('.sd-genetics__node--current');

    if (parentNodes.length === 0 || !childNode) return;

    function drawLines() {
        var svgRect = svg.parentElement.getBoundingClientRect();
        var w = svgRect.width;
        var h = 50;

        svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
        svg.setAttribute('width', w);
        svg.setAttribute('height', h);

        var ns = 'http://www.w3.org/2000/svg';
        svg.innerHTML = '';

        var centers = [];
        for (var i = 0; i < parentNodes.length; i++) {
            var r = parentNodes[i].getBoundingClientRect();
            centers.push(r.left + r.width / 2 - svgRect.left);
        }

        var childRect = childNode.getBoundingClientRect();
        var childCx = childRect.left + childRect.width / 2 - svgRect.left;
        var barY = 25;
        var lineColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--accent-green').trim() || '#00e676';

        for (var j = 0; j < centers.length; j++) {
            var line = document.createElementNS(ns, 'line');
            line.setAttribute('x1', centers[j]);
            line.setAttribute('y1', 0);
            line.setAttribute('x2', centers[j]);
            line.setAttribute('y2', barY);
            line.setAttribute('stroke', lineColor);
            line.setAttribute('stroke-width', '2');
            svg.appendChild(line);
        }

        if (centers.length > 1) {
            var hLine = document.createElementNS(ns, 'line');
            hLine.setAttribute('x1', Math.min.apply(null, centers));
            hLine.setAttribute('y1', barY);
            hLine.setAttribute('x2', Math.max.apply(null, centers));
            hLine.setAttribute('y2', barY);
            hLine.setAttribute('stroke', lineColor);
            hLine.setAttribute('stroke-width', '2');
            svg.appendChild(hLine);
        }

        var vLine = document.createElementNS(ns, 'line');
        vLine.setAttribute('x1', childCx);
        vLine.setAttribute('y1', centers.length > 1 ? barY : 0);
        vLine.setAttribute('x2', childCx);
        vLine.setAttribute('y2', h);
        vLine.setAttribute('stroke', lineColor);
        vLine.setAttribute('stroke-width', '2');
        svg.appendChild(vLine);
    }

    if (document.readyState === 'complete') {
        drawLines();
    } else {
        window.addEventListener('load', drawLines);
    }
    window.addEventListener('resize', drawLines);
})();
