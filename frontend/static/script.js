document.addEventListener('DOMContentLoaded', function() {
    const emailItems = document.querySelectorAll('.email-item');
    const senderInput = document.getElementById('sender');
    const subjectInput = document.getElementById('subject');
    const contentInput = document.getElementById('content');
    const processBtn = document.getElementById('process-btn');
    const resultsDiv = document.getElementById('results');
    const classificationResult = document.getElementById('classification-result');
    const classificationDetails = document.querySelector('.classification-details');
    const suggestedResponse = document.querySelector('.suggested-response');

    // Load email when clicked
    emailItems.forEach(item => {
        item.addEventListener('click', function() {
            senderInput.value = this.dataset.sender;
            subjectInput.value = this.dataset.subject;
            contentInput.value = this.dataset.content;
        });
    });

    // Process email
    processBtn.addEventListener('click', async function() {
        const sender = senderInput.value.trim();
        const subject = subjectInput.value.trim();
        const content = contentInput.value.trim();

        if (!sender || !subject || !content) {
            alert('Please fill in all fields');
            return;
        }

        try {
            const response = await fetch('http://localhost:8000/process-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    sender,
                    subject,
                    content
                })
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Display results
            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            resultsDiv.innerHTML = `<p class="error">Error processing email: ${error.message}</p>`;
        }
    });

    function displayResults(data) {
        classificationResult.classList.remove('hidden');
        
        // Classification details
        classificationDetails.innerHTML = `
            <p><strong>Main Category:</strong> <span class="category-tag">${data.classification.main_category}</span></p>
            <p><strong>Confidence:</strong> <span class="confidence ${data.classification.is_confident ? '' : 'low-confidence'}">${(data.classification.confidence * 100).toFixed(1)}%</span></p>
            ${data.classification.is_confident ? '' : '<p class="warning">⚠️ Low confidence in classification</p>'}
            <p><strong>Summary:</strong> <span class="category-tag">${data.classification.summary}</span></p>
            </p>
        `;
        
        // Suggested response
        suggestedResponse.textContent = data.response.suggested;
    }
});