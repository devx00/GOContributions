import { Component, ViewChild } from '@angular/core';


@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  title = 'GOContributor';
  showInput = true;
  orgname = "";
  showError = false;
  errorMessage: string;



  go(org:string) {
    this.errorMessage = null;
    this.showError = false;
    this.orgname = org;
    this.showInput = false;
  }

  clear() {
    this.orgname = null;
    this.showInput = true;
  }
  error(e) {
    this.clear();
    if (e.code === 404) {
      this.errorMessage = "Couldnt find that organization.";
    } else {
      this.errorMessage = e.message;
    }
    this.showError = true;
  }


}
