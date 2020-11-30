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
    if (e.code === 404) {
      this.clear();
      this.errorMessage = "Couldnt find that organization.";
      this.showError = true;
      console.log(this.errorMessage);
    }
  }


}
